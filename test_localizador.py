import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
import requests
from openpyxl import load_workbook
import servicos
from PyQt5 import QtCore, QtWidgets
from localizador_empresas import Janela


class ServicosTests(unittest.TestCase):
    def test_coordenadas(self):
        self.assertEqual(servicos.coordenadas("-23,5", "-46,6"), (-23.5, -46.6))
        for lat, lon in [("nan", 0), (91, 0), (0, 181), ("inf", 0)]:
            with self.assertRaises(ValueError):
                servicos.coordenadas(lat, lon)

    @patch("servicos.consultar")
    def test_osm_areas_endereco_e_avaliacao(self, call):
        call.return_value = {"elements": [{"type": "way", "center": {"lat": 1, "lon": 2}, "tags": {"name": "Mercado", "addr:street": "Rua A", "addr:housenumber": "20"}}]}
        rows = servicos.buscar("OSM", "", 5000, "Supermercados", 1, 2)
        query = call.call_args.kwargs["data"]["data"]
        self.assertIn('nwr["shop"="supermarket"]', query)
        self.assertEqual(rows[0], ["Mercado", "Rua A, 20", None, None, 1, 2])

    @patch("servicos.consultar")
    def test_osm_rejeita_injecao_e_resultado_parcial(self, call):
        with self.assertRaises(ValueError):
            servicos.buscar("OSM", "", 5000, 'cafe];out;', 1, 2)
        call.assert_not_called()
        call.return_value = {"remark": "runtime error", "elements": []}
        with self.assertRaises(ValueError):
            servicos.buscar("OSM", "", 5000, "cafe", 1, 2)

    @patch("servicos.consultar")
    def test_google_atual(self, call):
        call.return_value = {"places": [{"displayName": {"text": "Café"}, "location": {"latitude": 1, "longitude": 2}, "rating": 4.8}]}
        result = servicos.buscar("Google", "secret", 1000, "Cafeterias", 1, 2)
        self.assertEqual(result[0][2], 4.8)
        self.assertEqual(call.call_args.kwargs["json"]["includedTypes"], ["cafe"])

    @patch("servicos.consultar")
    def test_foursquare_atual(self, call):
        call.return_value = {"results": [{"name": "Café", "latitude": 1, "longitude": 2}]}
        self.assertEqual(servicos.buscar("Foursquare", "secret", 1000, "Cafeterias", 1, 2)[0][-2:], [1, 2])
        self.assertEqual(call.call_args.kwargs["headers"]["Authorization"], "Bearer secret")

    def test_limite_yelp(self):
        with self.assertRaises(ValueError):
            servicos.buscar("Yelp", "secret", 50000, "cafe", 1, 2)

    @patch("servicos.requests.request")
    def test_erro_nao_expoe_chave(self, call):
        call.side_effect = requests.ConnectionError("https://example.com/?key=SECRET")
        with self.assertRaises(ValueError) as err:
            servicos.consultar("GET", "https://example.com")
        self.assertNotIn("SECRET", str(err.exception))

    def test_excel_texto_numeros_e_formatacao(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.xlsx"
            servicos.salvar_excel(path, [["=HYPERLINK(\"https://example.com\")", "Rua A", 4.5, 20, -23.5, -46.6]])
            book = load_workbook(path)
            sheet = book.active
            self.assertEqual(sheet["A2"].data_type, "s")
            self.assertEqual(sheet["C2"].value, 4.5)
            self.assertEqual(sheet.freeze_panes, "A2")
            book.close()


class InterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.window = Janela()

    def tearDown(self):
        self.window.close()

    def test_inicial_sem_rede_e_sem_localizacao_falsa(self):
        self.assertEqual(self.window.lat.text(), "")
        self.assertEqual(self.window.api.currentText(), "OSM")
        self.assertFalse(self.window.export.isEnabled())

    def test_filtro_ordenacao_e_sem_edicao(self):
        self.window.api_busca = "OSM"
        self.window.resultados([["B", "Rua B", 4.5, 100, 1, 2], ["A", "Rua A", 3.0, 9, 3, 4]])
        self.window.proxy.sort(3, QtCore.Qt.AscendingOrder)
        self.assertEqual(self.window.proxy.index(0, 3).data(), 9)
        self.window.filtro.setText("Rua B")
        self.assertEqual(self.window.proxy.rowCount(), 1)
        self.assertEqual(self.window.table.editTriggers(), QtWidgets.QAbstractItemView.NoEditTriggers)
        self.window.falha("Falha de conexão")
        self.assertEqual(len(self.window.empresas), 2)

    def test_limite_visual_yelp(self):
        self.window.raio.setValue(50000)
        self.window.api.setCurrentText("Yelp")
        self.assertEqual(self.window.raio.value(), 40000)


if __name__ == "__main__":
    unittest.main()
