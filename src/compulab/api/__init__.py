"""Capa de entrada: API HTTP (FastAPI) y raíz de composición.

Traduce peticiones HTTP a llamadas de casos de uso y errores de dominio a
respuestas HTTP. La raíz de composición es el único lugar donde se decide qué
adaptador concreto se inyecta en cada puerto.
"""
