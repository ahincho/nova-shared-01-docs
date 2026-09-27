#!/usr/bin/env python3
"""Receta de migración de ADR-039: reescribe las coordenadas de los artefactos de Nova
Platform que cambiaron de nombre, y comprueba que cada repositorio siga las reglas del ADR.

Se corre sobre un repositorio, o sobre una carpeta que contiene varios. Por defecto solo
informa; con --apply escribe. --phase limita la receta a las filas de una fase, y conviene
pasarlo siempre: un consumidor solo migra cuando el nombre nuevo ya está publicado.

    python ops/rename-artifacts.py D:/Nova --phase 1
    python ops/rename-artifacts.py D:/Nova/nova-example-04-quarkus-reference --phase 1 --apply
    python ops/rename-artifacts.py D:/Nova --check

Qué reescribe, por cada fila de artifact-renames.json:
- en Gradle, "<groupId>:<artifactId viejo>[:<versión>]";
- en Maven, el <artifactId> de un bloque cuyo <groupId> es el del artefacto, su <version>
  literal y la propiedad <artifactId viejo>.version;
- en Quarkus, la clave y el valor de quarkus.index-dependency.*;
- la clave de SonarCloud <dueño>_<artifactId viejo>;
- cualquier otra mención del nombre viejo como palabra entera: README, settings.gradle.kts,
  la configuración de release-please.

Una versión literal menor que la primera publicada con el nombre nuevo sube a esa versión,
porque con el nombre nuevo la vieja no existe. Una versión que no es literal se deja y se avisa.
No renombra carpetas ni cambia la versión que declara un proyecto: eso se hace a mano en el
repositorio del artefacto, como explica ADR-039.
"""
import argparse
import fnmatch
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

BOM = b"\xef\xbb\xbf"
CONFIG_FILE = Path(__file__).resolve().parent / "artifact-renames.json"
NPM_PACKAGE = re.compile(r"@ahincho/[A-Za-z0-9._-]+")
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)")
# Un nombre como palabra entera. Un punto delante no cuenta: es el paquete de GitHub
# Packages (grupo.artifactId) o una clave, y esos se tratan con reglas propias.
LEFT = r"(?<![A-Za-z0-9_.-])"
RIGHT = r"(?![A-Za-z0-9_-])"
POM_NS = {"m": "http://maven.apache.org/POM/4.0.0"}


def load_config():
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def version_key(version):
    match = SEMVER.match(version)
    if not match:
        return None
    # Una preversión (1.0.0-SNAPSHOT) va antes que la versión que anuncia.
    release = 0 if version[match.end():] else 1
    return tuple(int(part) for part in match.groups()) + (release,)


class Rewriter:
    """Las reglas de una fila del mapa, compiladas una vez."""

    def __init__(self, row, owner):
        self.row = row
        group, old, new = (re.escape(row[k]) for k in ("groupId", "from", "to"))
        self.new = row["to"]
        self.gradle = re.compile(rf"([\"']){group}:{old}(:[^\"'\s]*)?\1")
        self.maven_group_first = re.compile(
            rf"(<groupId>\s*{group}\s*</groupId>\s*<artifactId>\s*){old}(\s*</artifactId>)")
        self.maven_artifact_first = re.compile(
            rf"(<artifactId>\s*){old}(\s*</artifactId>\s*<groupId>\s*{group}\s*</groupId>)")
        self.maven_version = re.compile(
            rf"(<groupId>\s*{group}\s*</groupId>\s*<artifactId>\s*{new}\s*</artifactId>\s*<version>\s*)([^<\s]+)(\s*</version>)")
        self.maven_property = re.compile(rf"<{old}\.version>\s*([^<\s]+)\s*</{old}\.version>")
        self.quarkus_key = re.compile(rf"(quarkus\.index-dependency\.){old}(\.)")
        self.sonar = re.compile(rf"{LEFT}{re.escape(owner)}_{old}{RIGHT}")
        self.owner = owner
        self.bare = re.compile(rf"{LEFT}{old}{RIGHT}")

    def bump(self, version, warnings, rel):
        since = self.row["since"]
        if not since:
            return version
        if version.startswith("${"):
            return version
        key = version_key(version)
        if key is None:
            warnings.append(f"versión no literal, revisar a mano: {rel}: {self.row['from']} {version}")
            return version
        return since if key < version_key(since) else version

    def apply(self, text, rel, warnings):
        count = 0

        def counted(repl):
            def inner(match):
                nonlocal count
                count += 1
                return repl(match)
            return inner

        def gradle(match):
            quote, tail = match.group(1), match.group(2)
            if tail and len(tail) > 1:
                tail = ":" + self.bump(tail[1:], warnings, rel)
            return f"{quote}{self.row['groupId']}:{self.new}{tail or ''}{quote}"

        text = self.gradle.sub(counted(gradle), text)
        if rel.endswith(".xml"):
            text = self.maven_group_first.sub(counted(lambda m: m.group(1) + self.new + m.group(2)), text)
            text = self.maven_artifact_first.sub(counted(lambda m: m.group(1) + self.new + m.group(2)), text)
            text = self.maven_version.sub(
                lambda m: m.group(1) + self.bump(m.group(2), warnings, rel) + m.group(3), text)
            text = self.maven_property.sub(counted(
                lambda m: f"<{self.new}.version>{self.bump(m.group(1), warnings, rel)}</{self.new}.version>"), text)
        text = self.quarkus_key.sub(counted(lambda m: m.group(1) + self.new + m.group(2)), text)
        text = self.sonar.sub(counted(lambda m: f"{self.owner}_{self.new}"), text)
        text = self.bare.sub(counted(lambda m: self.new), text)
        return text, count


def repo_roots(paths):
    """Cada carpeta con .git es un repositorio; una ruta sin .git se recorre buscándolos."""
    for path in paths:
        for current, dirs, files in os.walk(Path(path).resolve()):
            if ".git" in dirs or ".git" in files:
                dirs[:] = []
                yield Path(current)
            else:
                dirs[:] = sorted(d for d in dirs if d != "node_modules")


def text_files(root, config):
    skip_dirs, skip_files = set(config["skipDirs"]), set(config["skipFiles"])
    for current, dirs, files in os.walk(root):
        current = Path(current)
        dirs[:] = sorted(d for d in dirs
                         if d not in skip_dirs and not (current / d / ".git").exists())
        for name in sorted(files):
            if name in skip_files:
                continue
            path = current / name
            rel = path.relative_to(root).as_posix()
            # Un análisis fechado cuenta lo que pasó con el nombre que tenía entonces.
            if not any(fnmatch.fnmatchcase(rel, glob) for glob in config["historyGlobs"]):
                yield path, rel


def process_file(path, rel, rewriters, apply, warnings):
    raw = path.read_bytes()
    if b"\x00" in raw[:8192]:
        return 0, None
    has_bom = raw.startswith(BOM)
    try:
        text = raw[len(BOM):].decode("utf-8") if has_bom else raw.decode("utf-8")
    except UnicodeDecodeError:
        return 0, f"no es UTF-8, revisar a mano: {rel}"
    new_text, count = text, 0
    for rewriter in rewriters:
        new_text, n = rewriter.apply(new_text, rel, warnings)
        count += n
    if new_text == text:
        return 0, None
    # Ningún paquete npm cambia de nombre con esta receta. Si cambió, no se escribe.
    if Counter(NPM_PACKAGE.findall(text)) != Counter(NPM_PACKAGE.findall(new_text)):
        return 0, f"ERROR, cambiaría un paquete npm y no se tocó: {rel}"
    if apply:
        # En binario, para no tocar los finales de línea; el BOM se conserva si estaba.
        path.write_bytes((BOM if has_bom else b"") + new_text.encode("utf-8"))
    return count, None


# ---------------------------------------------------------------------------------------
# --check: las reglas 1 a 5 y 7 a 8 de ADR-039, repositorio por repositorio.
# ---------------------------------------------------------------------------------------

def read(path):
    try:
        return path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return ""


def gradle_facts(root):
    settings = read(root / "settings.gradle.kts")
    if not settings:
        return None
    name = re.search(r'rootProject\.name\s*=\s*"([^"]+)"', settings)
    modules = []
    for args in re.findall(r"include\(([^)]*)\)", settings):
        modules += [m.lstrip(":") for m in re.findall(r'"([^"]+)"', args)]
    props = read(root / "gradle.properties")
    build = read(root / "build.gradle.kts")
    group = re.search(r"(?m)^\s*group\s*=\s*([A-Za-z0-9_.-]+)\s*$", props) \
        or re.search(r'(?m)^\s*group\s*=\s*"([^"]+)"', build)
    return {"artifact": name.group(1) if name else None,
            "group": group.group(1) if group else None, "modules": modules}


def pom_facts(root):
    path = root / "pom.xml"
    if not path.exists():
        return None
    try:
        project = ET.parse(path).getroot()
    except ET.ParseError:
        return None

    def text(xpath):
        el = project.find(xpath, POM_NS)
        return el.text.strip() if el is not None and el.text else None

    modules = []
    for module in project.findall("m:modules/m:module", POM_NS):
        sub = root / module.text.strip() / "pom.xml"
        try:
            modules.append(ET.parse(sub).getroot().find("m:artifactId", POM_NS).text.strip())
        except (OSError, ET.ParseError, AttributeError):
            pass
    return {"artifact": text("m:artifactId"),
            "group": text("m:groupId") or text("m:parent/m:groupId"), "modules": modules}


def release_please(root):
    try:
        config = json.loads(read(root / ".release-please-config.json"))
        package = config["packages"]["."]
        return package.get("component"), package.get("package-name")
    except (ValueError, KeyError, TypeError):
        return None


def sonar_keys(root):
    keys = []
    for workflow in sorted((root / ".github" / "workflows").glob("*.yml")):
        keys += re.findall(r"sonar-project-key:\s*['\"]?([A-Za-z0-9_.:-]+)", read(workflow))
    return keys


def check_repo(root, config):
    name, owner, problems = root.name, config["owner"], []
    if name in config["checkExceptions"]:
        return [f"excepción: {config['checkExceptions'][name]}"], True
    example = re.match(r"^nova-example-\d{2}-(.+)$", name)
    component = re.match(r"^nova-(java|nestjs)-\d{2}-(.+)$", name)
    if not (example or component):
        return [], False
    technology = component.group(1) if component else None
    segment = example.group(1) if example else component.group(2)

    package_json = root / "package.json"
    # Un repositorio Java también puede traer package.json, por commitlint: manda el build.
    facts = gradle_facts(root) or pom_facts(root)
    if technology == "nestjs" or (example and not facts and package_json.exists()):
        try:
            package = json.loads(read(package_json))
        except ValueError:
            package = {}
        if segment == "platform":
            for sub in sorted((root / "packages").glob("*/package.json")):
                npm = json.loads(read(sub)).get("name", "")
                if not npm.startswith(f"@{owner}/nova-nestjs"):
                    problems.append(f"regla 7: paquete «{npm}», esperado «@{owner}/nova-nestjs[-<rol>]»")
        elif example:
            expected = f"nova-example-{segment}"
            if package.get("name") != expected:
                problems.append(f"regla 8: name «{package.get('name')}», esperado «{expected}»")
        else:
            expected = f"@{owner}/nova-nestjs-{segment}"
            if package.get("name") != expected:
                problems.append(f"regla 7: paquete «{package.get('name')}», esperado «{expected}»")
        return problems, False

    if not facts or not facts["artifact"]:
        return [], False
    artifact = facts["artifact"]
    expected = f"nova-example-{segment}" if example else f"nova-{segment}"
    rule = "regla 8" if example else "reglas 1 a 3"
    if artifact != expected:
        problems.append(f"{rule}: artifactId «{artifact}», esperado «{expected}»")
    if example and facts["group"] != config["exampleGroupId"]:
        problems.append(f"regla 8: groupId «{facts['group']}», esperado «{config['exampleGroupId']}»")

    family = next((t for t in config["typeSuffixes"] if segment.endswith(t)), None)
    if family and not example:
        for module in facts["modules"]:
            if not module.endswith(f"-{family}"):
                problems.append(f"regla 4: módulo «{module}», esperado «nova-<capacidad>-{family}»")

    rp = release_please(root)
    if rp:
        comp, package_name = rp
        if comp and comp != expected:
            problems.append(f"regla 5: componente de release-please «{comp}», esperado «{expected}»")
        wanted = f"{facts['group']}:{expected}"
        if package_name and package_name != wanted:
            problems.append(f"regla 5: package-name «{package_name}», esperado «{wanted}»")
    for key in sonar_keys(root):
        if key != f"{owner}_{expected}":
            problems.append(f"regla 5: clave de SonarCloud «{key}», esperado «{owner}_{expected}»")
    return problems, False


def main():
    parser = argparse.ArgumentParser(description="Receta de migración de ADR-039.")
    parser.add_argument("paths", nargs="+", help="repositorio o carpeta con repositorios")
    parser.add_argument("--apply", action="store_true", help="escribe los cambios")
    parser.add_argument("--phase", type=int, action="append",
                        help="aplica solo las filas de esa fase; se puede repetir")
    parser.add_argument("--list", action="store_true", help="muestra cada archivo que cambia")
    parser.add_argument("--check", action="store_true",
                        help="no reescribe: lista lo que no cumple las reglas de ADR-039")
    args = parser.parse_args()
    config = load_config()

    if args.check:
        print("Comprobación de ADR-039\n")
        total = 0
        for root in repo_roots(args.paths):
            problems, exception = check_repo(root, config)
            if exception:
                print(f"{root.name}: {problems[0]}")
                continue
            for problem in problems:
                print(f"{root.name}: {problem}")
            total += len(problems)
        print(f"\nTotal: {total} incumplimientos.")
        return 1 if total else 0

    rows = [r for r in config["renames"] if not args.phase or r["phase"] in args.phase]
    rewriters = [Rewriter(row, config["owner"]) for row in rows]
    mode = "APLICADO" if args.apply else "SIMULACIÓN (no se escribió nada; --apply para escribir)"
    phases = ", ".join(str(p) for p in sorted({r["phase"] for r in rows}))
    print(f"Receta de ADR-039, fases {phases} - {mode}\n")

    total_files = total_refs = 0
    errors = []
    for root in repo_roots(args.paths):
        files = refs = 0
        changed, warnings = [], []
        for path, rel in text_files(root, config):
            count, problem = process_file(path, rel, rewriters, args.apply, warnings)
            if problem:
                errors.append(f"{root.name}: {problem}")
            if count:
                files += 1
                refs += count
                changed.append(f"      {count:>3}  {rel}")
        if refs or warnings:
            print(f"{root.name:<48} {refs:>4} referencias en {files:>3} archivos")
            if args.list:
                print("\n".join(changed))
            for warning in warnings:
                print(f"      aviso: {warning}")
        total_files += files
        total_refs += refs

    print(f"\nTotal: {total_refs} referencias en {total_files} archivos.")
    for error in errors:
        print(error, file=sys.stderr)
    return 1 if any(e.split(": ", 1)[1].startswith("ERROR") for e in errors) else 0


if __name__ == "__main__":
    sys.exit(main())
