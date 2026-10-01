// Genera el esqueleto de la matriz de capacidades: una fila por capacidad y una columna por stack.
import { writeFileSync } from 'node:fs';

const status = {
  done: { bg: '#b2f2bb', stroke: '#2f9e44' },
  partial: { bg: '#fff3bf', stroke: '#d9480f' },
  pending: { bg: '#ffc9c9', stroke: '#e03131' },
  proposed: { bg: '#e5dbff', stroke: '#7048e8' },
  na: { bg: '#f1f3f5', stroke: '#868e96' },
};

// [capacidad, Spring Boot, Quarkus, NestJS]; cada celda es [estado, texto].
const rows = [
  ['Sobre de éxito', ['done', '08 starter 3.0.1'], ['partial', 'a mano con ApiResponse.ok'], ['done', 'núcleo 0.16.1']],
  ['Errores por capas (ADR-031)', ['done', '08 starter 3.0.1'], ['pending', 'decidido en ADR-050'], ['done', 'núcleo 0.16.1']],
  ['Secretos del entorno (ADR-042)', ['done', '23 secrets 1.2.0'], ['done', '23 extensión 1.2.0'], ['done', 'núcleo 0.16.1']],
  ['Vault y AWS Secrets Manager (ADR-049)', ['done', '23 secrets 1.2.0'], ['partial', '1.2.0; AWS en nativo por probar'], ['done', 'dos paquetes 0.16.1']],
  ['Idempotencia (ADR-047)', ['done', '25 idempotency 0.1.1'], ['pending', 'llega con plaza-catalog'], ['partial', 'deja pasar la clave']],
  ['Observabilidad (ADR-014 y ADR-032)', ['done', '09 starter 2.0.2'], ['pending', 'sin artefacto de Nova'], ['partial', 'logs con pino, sin OTel']],
  ['Borde y correlación (ADR-037)', ['pending', 'sin capa HTTP propia'], ['pending', 'sin capa HTTP propia'], ['done', 'núcleo 0.16.1']],
  ['Fallos de upstream (ADR-035)', ['pending', 'sin cliente HTTP de Nova'], ['pending', 'sin cliente HTTP de Nova'], ['done', 'núcleo 0.16.1, sin Proxy-Status']],
  ['Autenticación con Keycloak', ['pending', '06 keycloak: solo README'], ['pending', '11 extensión: solo README'], ['done', 'JWT contra JWKS']],
  ['Reglas de arquitectura', ['done', '07 architecture-rules 1.1.2'], ['partial', 'la librería, sin integración'], ['done', 'nova lint:arch']],
  ['Imagen nativa (ADR-045)', ['done', 'toolchain y starters 3.0.1'], ['partial', 'secretos sí; estándar con ADR-050'], ['na', 'no aplica']],
  ['Toolchain de build', ['done', '24 gradle-toolchain 2.0.0'], ['pending', 'sin plugin quarkus-service'], ['done', 'nova-nestjs-toolchain 0.16.1']],
  ['Generadores', ['partial', '17 archetype sin release'], ['partial', '18 y 19 por actualizar'], ['done', 'schematics 0.16.1']],
  ['Plantillas de servicio (ADR-051)', ['pending', 'nova-template-01 (ADR-051)'], ['pending', 'nova-template-02, hoy el 19'], ['pending', 'nova-template-03, hoy el 08']],
  ['Outbox transaccional (ADR-048)', ['proposed', 'propuesta, docs #14'], ['proposed', 'propuesta, docs #14'], ['proposed', 'propuesta, docs #14']],
];

const el = [];
const box = (id, x, y, w, h, s, text, fontSize = 17, extra = {}) =>
  el.push({ type: 'rectangle', id, x, y, width: w, height: h, roundness: { type: 3 }, backgroundColor: s.bg, strokeColor: s.stroke, label: { text, fontSize }, ...extra });

el.push({ type: 'cameraUpdate', width: 800, height: 600, x: 0, y: 0 });
el.push({ type: 'text', id: 'title', x: 40, y: 24, text: 'Nova Platform: capacidades por stack', fontSize: 36 });
el.push({ type: 'text', id: 'sub', x: 40, y: 76, text: 'Estado al 2026-10-01, con la versión publicada que lo cumple.', fontSize: 18, strokeColor: '#495057' });
el.push({ type: 'cameraUpdate', width: 1600, height: 1200, x: 0, y: 0 });

const cols = [40, 440, 820, 1200];
const widths = [380, 360, 360, 360];
const headers = [
  ['Capacidad', { bg: '#f1f3f5', stroke: '#495057' }],
  ['Spring Boot', { bg: '#b2f2bb', stroke: '#2f9e44' }],
  ['Quarkus', { bg: '#a5d8ff', stroke: '#1971c2' }],
  ['NestJS', { bg: '#ffc9c9', stroke: '#c92a2a' }],
];
headers.forEach(([text, s], i) => box(`h${i}`, cols[i], 120, widths[i], 50, s, text, 22));

rows.forEach((row, r) => {
  const y = 186 + r * 60;
  box(`c${r}`, cols[0], y, widths[0], 52, { bg: '#ffffff', stroke: '#495057' }, row[0], 17);
  row.slice(1).forEach(([state, text], c) => box(`m${r}-${c}`, cols[c + 1], y, widths[c + 1], 52, status[state], text, 17));
});

const legend = [
  ['done', 'hecho'],
  ['partial', 'parcial'],
  ['pending', 'pendiente'],
  ['proposed', 'propuesto en un ADR'],
  ['na', 'no aplica'],
];
const ly = 186 + rows.length * 60 + 20;
legend.forEach(([state, text], i) => box(`lg${i}`, 40 + i * 300, ly, 280, 44, status[state], text, 17));

writeFileSync(new URL('../src/05-capacidades.json', import.meta.url), JSON.stringify(el, null, 0).replaceAll('},{', '},\n{') + '\n');
console.log(`${el.length} elementos, leyenda en y=${ly}`);
