"""Función de aptitud FF-1: la regla de dependencia entre capas.

Propiedad del diseño que protege: las dependencias apuntan hacia el dominio.

    api  ->  infraestructura  ->  aplicacion  ->  dominio

La verifica import-linter con el contrato ``capas-hexagonales`` de
pyproject.toml. Esta prueba lo ejecuta de dos formas:

1. Sobre el código real: debe cumplirse (si no, el build falla).
2. Sobre un paquete *plantado* con una violación a propósito (el dominio
   importa la aplicación): el MISMO contrato debe detectarla. Así sabemos que
   la función de aptitud no está pasando por estar mal configurada.
"""

import subprocess
import sys
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
LINT_IMPORTS = Path(sys.executable).parent / "lint-imports"


def contrato_real() -> dict:
    configuracion = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))
    return configuracion["tool"]["importlinter"]


def correr_lint_imports(directorio: Path, config: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(LINT_IMPORTS), "--config", str(config), "--no-cache", "--no-logo"],
        cwd=directorio,
        env={"PYTHONPATH": str(directorio), "PATH": ""},
        capture_output=True,
        text=True,
        check=False,
    )


def test_el_codigo_respeta_la_regla_de_dependencia():
    resultado = correr_lint_imports(RAIZ / "src", RAIZ / "pyproject.toml")
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert "1 kept, 0 broken" in resultado.stdout


def plantar_paquete(raiz: Path, modulo_violador: str, codigo: str) -> None:
    """Crea un paquete 'plantado' con las mismas capas que compulab."""
    for capa in ("", "dominio", "aplicacion", "infraestructura", "api"):
        carpeta = raiz / "plantado" / capa
        carpeta.mkdir(parents=True, exist_ok=True)
        (carpeta / "__init__.py").write_text("")
    (raiz / "plantado" / "aplicacion" / "servicio.py").write_text("VALOR = 1\n")
    (raiz / "plantado" / "infraestructura" / "bd.py").write_text("VALOR = 2\n")
    (raiz / "plantado" / Path(*modulo_violador.split("."))).with_suffix(".py").write_text(codigo)


def config_plantada(raiz: Path) -> Path:
    """El mismo contrato de pyproject.toml, apuntando al paquete plantado."""
    contrato = contrato_real()["contracts"][0]
    capas = ", ".join(f'"{c.replace("compulab", "plantado")}"' for c in contrato["layers"])
    config = raiz / "plantado.toml"
    config.write_text(
        "[tool.importlinter]\n"
        'root_package = "plantado"\n\n'
        "[[tool.importlinter.contracts]]\n"
        f'id = "{contrato["id"]}"\n'
        f'name = "{contrato["name"]}"\n'
        f'type = "{contrato["type"]}"\n'
        f"layers = [{capas}]\n"
    )
    return config


def test_detecta_un_dominio_que_importa_la_aplicacion(tmp_path):
    plantar_paquete(tmp_path, "dominio.malo", "from plantado.aplicacion import servicio\n")
    resultado = correr_lint_imports(tmp_path, config_plantada(tmp_path))
    assert resultado.returncode != 0
    assert "BROKEN" in resultado.stdout
    assert "plantado.dominio.malo" in resultado.stdout


def test_detecta_una_aplicacion_que_importa_la_infraestructura(tmp_path):
    plantar_paquete(tmp_path, "aplicacion.mala", "import plantado.infraestructura.bd\n")
    resultado = correr_lint_imports(tmp_path, config_plantada(tmp_path))
    assert resultado.returncode != 0
    assert "plantado.aplicacion.mala" in resultado.stdout
