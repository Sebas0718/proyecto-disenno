"""Prueba de humo: confirma que el paquete se instala y se puede importar."""

import compulab


def test_el_paquete_se_puede_importar():
    assert compulab.__doc__ is not None
