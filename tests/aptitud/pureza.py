"""Verificador de pureza del dominio (base de la función de aptitud FF-2).

El enunciado exige: "Ningún acceso real a red, archivos o reloj dentro del
dominio". Este verificador recorre el árbol sintáctico (módulo ``ast``) de
cada archivo del dominio y reporta:

- imports de módulos que tocan el exterior (red, archivos, procesos, bases de
  datos, frameworks, hora del sistema, azar);
- llamadas que leen el reloj (``datetime.now()``, ``date.today()``...);
- llamadas a ``open()``.

Se usa el árbol sintáctico y no una búsqueda de texto para no confundir un
comentario o un string que diga "datetime.now" con una llamada real.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

MODULOS_PROHIBIDOS = frozenset(
    {
        # archivos y sistema operativo
        "os", "io", "pathlib", "shutil", "tempfile", "glob", "sys", "subprocess",
        # red
        "socket", "ssl", "http", "urllib", "requests", "httpx", "smtplib",
        # bases de datos y frameworks
        "sqlite3", "psycopg", "psycopg2", "sqlalchemy", "fastapi", "starlette", "pydantic",
        # reloj y azar
        "time", "random", "secrets", "uuid", "zoneinfo",
    }
)  # fmt: skip
LECTURAS_DE_RELOJ = frozenset({"now", "today", "utcnow", "fromtimestamp", "utcfromtimestamp"})
DUENOS_DEL_RELOJ = frozenset({"datetime", "date"})
FUNCIONES_PROHIBIDAS = frozenset({"open", "input", "print"})


@dataclass(frozen=True)
class Violacion:
    archivo: Path
    linea: int
    detalle: str

    def __str__(self) -> str:
        return f"{self.archivo}:{self.linea}: {self.detalle}"


def _raiz(nombre: str) -> str:
    return nombre.split(".")[0]


class _Visitante(ast.NodeVisitor):
    def __init__(self, archivo: Path) -> None:
        self.archivo = archivo
        self.violaciones: list[Violacion] = []

    def _reportar(self, nodo: ast.AST, detalle: str) -> None:
        self.violaciones.append(Violacion(self.archivo, getattr(nodo, "lineno", 0), detalle))

    def visit_Import(self, nodo: ast.Import) -> None:
        for alias in nodo.names:
            if _raiz(alias.name) in MODULOS_PROHIBIDOS:
                self._reportar(nodo, f"import prohibido en el dominio: {alias.name}")

    def visit_ImportFrom(self, nodo: ast.ImportFrom) -> None:
        if nodo.module and nodo.level == 0 and _raiz(nodo.module) in MODULOS_PROHIBIDOS:
            self._reportar(nodo, f"import prohibido en el dominio: {nodo.module}")

    def visit_Call(self, nodo: ast.Call) -> None:
        funcion = nodo.func
        if isinstance(funcion, ast.Attribute) and funcion.attr in LECTURAS_DE_RELOJ:
            dueno = funcion.value
            nombre = dueno.attr if isinstance(dueno, ast.Attribute) else getattr(dueno, "id", "")
            if nombre in DUENOS_DEL_RELOJ:
                self._reportar(nodo, f"lectura del reloj del sistema: {nombre}.{funcion.attr}()")
        if isinstance(funcion, ast.Name) and funcion.id in FUNCIONES_PROHIBIDAS:
            self._reportar(nodo, f"llamada prohibida en el dominio: {funcion.id}()")
        self.generic_visit(nodo)


def buscar_violaciones(directorio: Path) -> list[Violacion]:
    """Devuelve todas las violaciones de pureza en los .py bajo ``directorio``."""
    violaciones: list[Violacion] = []
    for archivo in sorted(directorio.rglob("*.py")):
        visitante = _Visitante(archivo)
        visitante.visit(ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo)))
        violaciones.extend(visitante.violaciones)
    return violaciones
