# ADR-0013 · Pantallas en HTML/CSS/JS sin framework, servidas por la API

- **Estado:** aceptada

## Contexto
Se piden pantallas que "tomen en cuenta aspectos de diseño estudiados para la UX/UI".
No es necesario que se conecten a la base de datos. El equipo debe poder explicar
todo el código.

## Decisión
- HTML semántico, CSS con variables (tokens) y modo oscuro, y JavaScript con módulos ES nativos.
- Sin compilación, sin npm y sin CDN.
- FastAPI sirve la carpeta `web/` como archivos estáticos.

## Alternativas consideradas
| Alternativa | Por qué no |
|-------------|------------|
| React + Vite | Obliga a explicar componentes, estado, JSX y la cadena de compilación. No mejora la UX de 4 pantallas. |
| Plantillas en el servidor (Jinja2) | Mezcla la presentación con la API y hace menos fluida la validación en vivo. |

## Consecuencias
- **A favor:** cero dependencias de front end, y abre en cualquier navegador moderno.
- **En contra:** el DOM se actualiza "a mano". El helper `el()` de `ui.js` lo mantiene legible.
