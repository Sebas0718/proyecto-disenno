"""Capa de aplicación: casos de uso y puertos.

Cada caso de uso coordina objetos del dominio para cumplir una petición
(p. ej. "asignar un turno"). Lo que necesita del exterior (repositorios, reloj,
notificaciones, exportar archivos) lo declara como un *puerto*: una interfaz
(typing.Protocol) que los adaptadores de infraestructura implementan y que se
inyecta desde afuera. Depende solo del dominio.
"""
