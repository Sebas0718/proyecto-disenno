"""Capa de dominio: entidades, objetos de valor y reglas del negocio.

Es el centro de la arquitectura. Solo puede usar la biblioteca estándar de Python
y nunca toca el mundo exterior: nada de base de datos, red, archivos ni reloj del
sistema. Cuando una regla necesita "la hora actual", la recibe como parámetro.
"""
