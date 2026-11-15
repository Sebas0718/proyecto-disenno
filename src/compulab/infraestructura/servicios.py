"""Adaptadores de los puertos de servicios externos.

- ``RelojDelSistema``: la hora real de Costa Rica (único lugar que la consulta).
- ``NotificadorDeRegistro``: deja los avisos en el log; en producción se
  cambiaría por correo institucional sin tocar ningún caso de uso.
- ``DirectorioEnMemoria``: simula el directorio del Centro de Cómputo.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from compulab.dominio.comun.usuario import Usuario

ZONA_COSTA_RICA = ZoneInfo("America/Costa_Rica")

registro = logging.getLogger("compulab.notificaciones")


class RelojDelSistema:
    def ahora(self) -> datetime:
        # Hora local de Costa Rica sin zona horaria (ADR-0009); al minuto.
        return datetime.now(ZONA_COSTA_RICA).replace(tzinfo=None, second=0, microsecond=0)


@dataclass(frozen=True, slots=True)
class Notificacion:
    destinatario_id: str
    asunto: str
    mensaje: str


class NotificadorDeRegistro:
    """Registra cada aviso en el log y guarda los últimos para mostrarlos en pantalla."""

    def __init__(self, maximo: int = 200) -> None:
        self._enviadas: list[Notificacion] = []
        self._maximo = maximo

    def notificar(self, destinatario_id: str, asunto: str, mensaje: str) -> None:
        registro.info("Aviso para %s: %s — %s", destinatario_id, asunto, mensaje)
        self._enviadas.append(Notificacion(destinatario_id, asunto, mensaje))
        del self._enviadas[: -self._maximo]

    def de(self, destinatario_id: str) -> list[Notificacion]:
        return [n for n in reversed(self._enviadas) if n.destinatario_id == destinatario_id]


class DirectorioEnMemoria:
    """Directorio institucional simulado (ADR-0011)."""

    def __init__(self, usuarios: Iterable[Usuario]) -> None:
        self._usuarios = {u.id: u for u in usuarios}

    def buscar(self, usuario_id: str) -> Usuario | None:
        return self._usuarios.get(usuario_id)

    def listar(self) -> list[Usuario]:
        return list(self._usuarios.values())
