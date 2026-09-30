#!/usr/bin/env python3
"""Receta de migración de ADR-038: reescribe las referencias a los repositorios de Nova
Platform que cambiaron de nombre.

Se corre sobre un repositorio, o sobre una carpeta que contiene varios. Por defecto solo
informa; con --apply escribe.

    python ops/rename-repos.py D:/Nova
    python ops/rename-repos.py D:/Nova --apply
    python ops/rename-repos.py D:/Nova --apply --remotes

Qué reescribe y qué no está explicado en ADR-038. En corto: solo toca un nombre cuando va
anclado al dueño (`ahincho/<repo>`), porque un nombre suelto puede ser otra cosa. `nova-bom`
es a la vez el repositorio y el artifactId del BOM, y `@ahincho/nova-nestjs` es el paquete
npm: reescribir cualquiera de los dos sería un cambio incompatible para cada consumidor.
"""
import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

BOM = b"\xef\xbb\xbf"
MAP_FILE = Path(__file__).resolve().parent / "repo-renames.json"
# Todo lo que empieza con @dueño/ es un paquete npm, y un paquete no se renombra nunca.
NPM_PACKAGE = re.compile(r"@ahincho/[A-Za-z0-9._-]+")


def load_map():
    config = json.loads(MAP_FILE.read_text(encoding="utf-8"))
    renames = config["renames"]
    # El más largo primero, para que ninguna alternativa se coma a otra que la contiene.
    names = "|".join(re.escape(n) for n in sorted(renames, key=len, reverse=True))
    owner = re.escape(config["owner"])
    # Anclado al dueño. Ni una letra ni un @ delante: `@ahincho/` es un paquete npm.
    anchored = re.compile(rf"(?<![@A-Za-z0-9_.-]){owner}/({names})(?![A-Za-z0-9_-])")
    # Nombre suelto: solo en los archivos que enumeran repositorios, ver bareNameFiles.
    bare = re.compile(rf"(?<![@/A-Za-z0-9_.-])({names})(?![A-Za-z0-9_-])")
    return config, renames, anchored, bare


def repo_roots(paths):
    """Cada carpeta con .git es un repositorio; una ruta sin .git se recorre buscándolos."""
    for path in paths:
        for current, dirs, files in os.walk(Path(path).resolve()):
            # .git puede ser un archivo, en un worktree o un submódulo.
            if ".git" in dirs or ".git" in files:
                dirs[:] = []
                yield Path(current)
            else:
                dirs[:] = sorted(d for d in dirs if d != "node_modules")


def text_files(root, config):
    skip_dirs, skip_files = set(config["skipDirs"]), set(config["skipFiles"])
    for current, dirs, files in os.walk(root):
        current = Path(current)
        # Se podan antes de entrar: ni .git ni node_modules se recorren. Un repositorio
        # anidado tampoco, porque se procesa como raíz propia.
        dirs[:] = sorted(d for d in dirs
                         if d not in skip_dirs and not (current / d / ".git").exists())
        for name in sorted(files):
            if name in skip_files:
                continue
            path = current / name
            rel = path.relative_to(root).as_posix()
            # Un análisis fechado cuenta lo que pasó con el nombre que tenía entonces:
            # reescribirlo cambiaría la historia, no la corregiría.
            if not any(fnmatch.fnmatchcase(rel, glob) for glob in config["historyGlobs"]):
                yield path, rel


def rewrite(text, pattern, renames, owner=None):
    count = 0

    def replace(match):
        nonlocal count
        count += 1
        new = renames[match.group(1)]
        return f"{owner}/{new}" if owner else new

    return pattern.sub(replace, text), count


def process_file(path, rel, config, renames, anchored, bare, apply):
    raw = path.read_bytes()
    if b"\x00" in raw[:8192]:
        return 0, None
    has_bom = raw.startswith(BOM)
    try:
        text = raw[len(BOM):].decode("utf-8") if has_bom else raw.decode("utf-8")
    except UnicodeDecodeError:
        return 0, f"no es UTF-8, revisar a mano: {rel}"

    new_text, count = rewrite(text, anchored, renames, owner=config["owner"])
    if rel in config["bareNameFiles"]:
        new_text, bare_count = rewrite(new_text, bare, renames)
        count += bare_count

    if count == 0:
        return 0, None
    # La garantía de ADR-038: ningún paquete npm cambia de nombre. Si cambió, no se escribe.
    if Counter(NPM_PACKAGE.findall(text)) != Counter(NPM_PACKAGE.findall(new_text)):
        return 0, f"ERROR, cambiaría un paquete npm y no se tocó: {rel}"
    if apply:
        # Se escribe en binario para no cambiar los finales de línea, y el BOM se conserva
        # si el archivo lo traía.
        path.write_bytes((BOM if has_bom else b"") + new_text.encode("utf-8"))
    return count, None


def pending_mentions(path, rel, config, bare):
    """Nombres viejos que quedan sueltos, en prosa: son los pasos manuales de la migración."""
    if rel in config["bareNameFiles"]:
        return 0
    try:
        text = path.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError:
        return 0
    return len(bare.findall(text))


def update_remote(root, anchored, renames, owner, apply):
    try:
        url = subprocess.run(["git", "-C", str(root), "remote", "get-url", "origin"],
                             capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    new_url, count = rewrite(url, anchored, renames, owner=owner)
    if count and apply:
        subprocess.run(["git", "-C", str(root), "remote", "set-url", "origin", new_url], check=True)
    return new_url if count else None


def main():
    parser = argparse.ArgumentParser(description="Receta de migración de ADR-038.")
    parser.add_argument("paths", nargs="+", help="repositorio o carpeta con repositorios")
    parser.add_argument("--apply", action="store_true", help="escribe los cambios")
    parser.add_argument("--remotes", action="store_true", help="actualiza también el origin de cada clon")
    parser.add_argument("--list", action="store_true", help="muestra cada archivo que cambia")
    args = parser.parse_args()

    config, renames, anchored, bare = load_map()
    mode = "APLICADO" if args.apply else "SIMULACIÓN (no se escribió nada; --apply para escribir)"
    print(f"Receta de ADR-038 - {mode}\n")

    total_files = total_refs = total_pending = 0
    errors = []
    for root in repo_roots(args.paths):
        files = refs = pending = 0
        changed = []
        for path, rel in text_files(root, config):
            count, problem = process_file(path, rel, config, renames, anchored, bare, args.apply)
            if problem:
                errors.append(f"{root.name}: {problem}")
            if count:
                files += 1
                refs += count
                changed.append(f"      {count:>3}  {rel}")
            pending += pending_mentions(path, rel, config, bare)
        remote = update_remote(root, anchored, renames, config["owner"], args.apply) if args.remotes else None

        line = f"{root.name:<48} {refs:>4} referencias en {files:>3} archivos"
        if pending:
            line += f"   | {pending} menciones sueltas para revisar a mano"
        print(line)
        if remote:
            print(f"      origin -> {remote}")
        if args.list:
            print("\n".join(changed))
        total_files += files
        total_refs += refs
        total_pending += pending

    print(f"\nTotal: {total_refs} referencias en {total_files} archivos; "
          f"{total_pending} menciones sueltas quedan para revisión manual.")
    for error in errors:
        print(error, file=sys.stderr)
    return 1 if any(e.split(": ", 1)[1].startswith("ERROR") for e in errors) else 0


if __name__ == "__main__":
    sys.exit(main())
