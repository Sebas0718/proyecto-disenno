"""Capa de infraestructura: adaptadores que implementan los puertos.

Aquí vive todo lo que toca el mundo exterior: repositorios en PostgreSQL y en
memoria, el reloj del sistema, el exportador del archivo CSV para Becas y el
notificador. Ninguna regla de negocio debe vivir en esta capa.
"""
