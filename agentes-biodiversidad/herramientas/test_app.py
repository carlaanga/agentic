"""Pruebas de las funciones puras del servidor de herramientas (sin red).

    docker compose run --rm gbif-tools python -m unittest -v
"""
import unittest
from datetime import date

from app import a_iso, normalizar_anio


class TestNormalizarAnio(unittest.TestCase):
    def test_vacio(self):
        self.assertIsNone(normalizar_anio(None))
        self.assertIsNone(normalizar_anio(""))

    def test_un_anio_y_rango_pasan_igual(self):
        self.assertEqual(normalizar_anio("2020"), "2020")
        self.assertEqual(normalizar_anio("2020,2026"), "2020,2026")
        self.assertEqual(normalizar_anio("2020, 2026"), "2020,2026")

    def test_desde_se_cierra_en_el_anio_actual(self):
        self.assertEqual(normalizar_anio("2020,*"), f"2020,{date.today().year}")

    def test_hasta_se_abre_por_abajo(self):
        self.assertEqual(normalizar_anio("*,1950"), "1600,1950")


class TestAIso(unittest.TestCase):
    def test_codigo_iso(self):
        self.assertEqual(a_iso("cl"), "CL")
        self.assertEqual(a_iso("CO"), "CO")

    def test_nombre_en_espanol(self):
        self.assertEqual(a_iso("Chile"), "CL")
        self.assertEqual(a_iso("México"), "MX")
        self.assertEqual(a_iso("república dominicana"), "DO")

    def test_desconocido_pasa_tal_cual(self):
        self.assertIsNone(a_iso(None))
        self.assertEqual(a_iso("Atlántida"), "Atlántida")


if __name__ == "__main__":
    unittest.main()
