# ADR-0011 · Directorio institucional detrás de un puerto (simulado en el prototipo)

- **Estado:** aceptada

## Contexto
"El directorio institucional [...] es el que dice quién es quién cuando alguien entra."
No hay acceso real al directorio del TEC durante el curso.

## Decisión
- Puerto `DirectorioInstitucional`, con `buscar(id)` y `listar()`.
- En el prototipo lo implementa `DirectorioEnMemoria`, con usuarios de demostración.
- La sesión se simula con la cabecera HTTP `X-Usuario-Id`, que la pantalla toma de un selector "Entrar como".
- En producción, un adaptador OIDC o LDAP validaría un token. Ningún caso de uso cambia.

## Consecuencias
- **A favor:** la demo permite cambiar de rol en un clic y mostrar los permisos.
- **En contra:** el prototipo **no es seguro**, porque cualquiera puede enviar la cabecera. Es aceptable en un prototipo académico y está documentado como mejora prioritaria.
