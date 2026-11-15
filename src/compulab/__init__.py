"""CompuLab: administración de los laboratorios de cómputo de la Escuela.

El paquete sigue una arquitectura hexagonal (puertos y adaptadores):

    dominio  <-  aplicacion  <-  infraestructura / api

Las flechas indican quién puede importar a quién: el dominio no conoce a nadie,
la aplicación solo conoce al dominio, y los adaptadores (infraestructura y api)
conocen a ambos. Esa regla se verifica con funciones de aptitud en tests/aptitud.
"""
