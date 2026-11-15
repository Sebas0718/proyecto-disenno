# ADR-0009 · Hora local de Costa Rica sin zona horaria

- **Estado:** aceptada

## Contexto
Todos los usuarios y laboratorios están en Costa Rica (UTC-6), que **no** cambia de
horario en verano. Las reglas hablan de hora local: "seis de la tarde", "sábado".

## Decisión
- El dominio maneja `datetime` **sin zona horaria**, entendido como hora local de Costa Rica.
- `IntervaloTiempo` rechaza fechas con zona, para evitar mezclarlas por accidente.
- El único lugar que lee el reloj real es el adaptador `RelojDelSistema`, que convierte desde `America/Costa_Rica`.
- En PostgreSQL se usa `timestamp without time zone`.

## Alternativas consideradas
| Alternativa | Por qué no |
|-------------|------------|
| Todo en UTC y convertir al mostrar | Es correcto en sistemas multizona, pero aquí obligaría a convertir para evaluar "18:00" y "sábado", y eso invita a errores. |
| `timestamptz` en la base | No aporta nada sin multizona. |

## Consecuencias
- **A favor:** las reglas se leen igual que en el enunciado.
- **En contra:** si algún día hubiera laboratorios en otra zona, habría que migrar a UTC. Es poco probable y está documentado.
