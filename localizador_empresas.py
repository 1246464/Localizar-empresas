"""
Localizador de Empresas
Sistema para buscar empresas próximas usando múltiplas APIs de geolocalização
Suporta: Google Places, Yelp, Foursquare e OpenStreetMap
"""

import requests
import pandas as pd
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QThread, pyqtSignal
import sys


class BuscaThread(QThread):
    """Thread para fazer busca em background sem travar a interface"""
    finalizado = pyqtSignal(list, str)
    erro = pyqtSignal(str)

    def __init__(self, api, api_key, raio, segmento, latitude, longitude):
        super().__init__()
        self.api = api
        self.api_key = api_key
        self.raio = raio
        self.segmento = segmento
        self.latitude = latitude
        self.longitude = longitude

    def run(self):
        try:
            if self.api == "Google":
                empresas = self.buscar_google()
            elif self.api == "Yelp":
                empresas = self.buscar_yelp()
            elif self.api == "Foursquare":
                empresas = self.buscar_foursquare()
            else:  # OpenStreetMap
                empresas = self.buscar_osm()
            
            self.finalizado.emit(empresas, self.api)
        except Exception as e:
            self.erro.emit(f"Erro na busca: {str(e)}")

    def buscar_google(self):
        url = (
            f"https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            f"?location={self.latitude},{self.longitude}"
            f"&radius={self.raio}"
            f"&type={self.segmento}"
            f"&key={self.api_key}"
        )
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == "REQUEST_DENIED":
            raise Exception(f"API negada: {data.get('error_message', 'Verifique sua chave')}")
        
        empresas = []
        for place in data.get("results", []):
            empresas.append([
                place.get("name", "N/A"),
                place.get("vicinity", "N/A"),
                place.get("rating", "N/A"),
                place.get("user_ratings_total", "N/A"),
                place["geometry"]["location"]["lat"],
                place["geometry"]["location"]["lng"]
            ])
        return empresas

    def buscar_yelp(self):
        url = "https://api.yelp.com/v3/businesses/search"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        params = {
            "term": self.segmento,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "radius": min(int(self.raio), 40000),  # Yelp tem limite de 40km
            "limit": 50
        }
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        empresas = []
        for business in data.get("businesses", []):
            empresas.append([
                business.get("name", "N/A"),
                business.get("location", {}).get("address1", "N/A"),
                business.get("rating", "N/A"),
                business.get("review_count", "N/A"),
                business.get("coordinates", {}).get("latitude", "N/A"),
                business.get("coordinates", {}).get("longitude", "N/A")
            ])
        return empresas

    def buscar_foursquare(self):
        url = "https://api.foursquare.com/v3/places/search"
        headers = {"Authorization": self.api_key}
        params = {
            "ll": f"{self.latitude},{self.longitude}",
            "radius": int(self.raio),
            "query": self.segmento,
            "limit": 50
        }
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        empresas = []
        for place in data.get("results", []):
            loc = place.get("geocodes", {}).get("main", {})
            endereco = place.get("location", {}).get("formatted_address", "N/A")
            if isinstance(endereco, list):
                endereco = ", ".join(endereco)
            
            empresas.append([
                place.get("name", "N/A"),
                endereco,
                "N/A",  # Foursquare não fornece rating público na v3
                "N/A",
                loc.get("latitude", "N/A"),
                loc.get("longitude", "N/A")
            ])
        return empresas

    def buscar_osm(self):
        # OpenStreetMap Overpass API
        url = (
            f"https://overpass-api.de/api/interpreter"
            f"?data=[out:json];node[amenity={self.segmento}]"
            f"(around:{self.raio},{self.latitude},{self.longitude});out;"
        )
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        empresas = []
        for element in data.get("elements", []):
            tags = element.get("tags", {})
            empresas.append([
                tags.get("name", "Sem nome"),
                tags.get("addr:street", "N/A"),
                tags.get("amenity", "N/A"),
                "N/A",
                element.get("lat", "N/A"),
                element.get("lon", "N/A")
            ])
        return empresas


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(750, 650)
        Dialog.setStyleSheet("background-color: #f0f0f0")
        Dialog.setWindowTitle("Localizador de Empresas")

        # Título
        self.label_titulo = QtWidgets.QLabel("🔍 LOCALIZADOR DE EMPRESAS", Dialog)
        self.label_titulo.setGeometry(QtCore.QRect(150, 20, 450, 45))
        font_titulo = QtGui.QFont("Arial", 18, QtGui.QFont.Bold)
        self.label_titulo.setFont(font_titulo)
        self.label_titulo.setStyleSheet("color: #2c3e50; background: transparent;")

        # Labels
        label_style = "color: #34495e; font-weight: bold; background: transparent;"
        
        self.label_api_key = QtWidgets.QLabel("API Key:", Dialog)
        self.label_api_key.setGeometry(QtCore.QRect(10, 85, 100, 20))
        self.label_api_key.setStyleSheet(label_style)

        self.label_segmento = QtWidgets.QLabel("Segmento:", Dialog)
        self.label_segmento.setGeometry(QtCore.QRect(10, 115, 100, 20))
        self.label_segmento.setStyleSheet(label_style)

        self.label_raio = QtWidgets.QLabel("Raio (metros):", Dialog)
        self.label_raio.setGeometry(QtCore.QRect(370, 85, 100, 20))
        self.label_raio.setStyleSheet(label_style)

        self.label_local = QtWidgets.QLabel("Localização:", Dialog)
        self.label_local.setGeometry(QtCore.QRect(370, 115, 100, 20))
        self.label_local.setStyleSheet(label_style)

        self.label_api = QtWidgets.QLabel("API:", Dialog)
        self.label_api.setGeometry(QtCore.QRect(600, 85, 50, 20))
        self.label_api.setStyleSheet(label_style)

        # Inputs
        input_style = """
            QLineEdit {
                background-color: white;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                padding: 5px;
            }
            QLineEdit:focus {
                border: 2px solid #3498db;
            }
        """

        self.lineEdit_api = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_api.setGeometry(QtCore.QRect(110, 82, 240, 28))
        self.lineEdit_api.setStyleSheet(input_style)
        self.lineEdit_api.setPlaceholderText("Cole sua API Key aqui")

        self.lineEdit_segmento = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_segmento.setGeometry(QtCore.QRect(110, 112, 240, 28))
        self.lineEdit_segmento.setStyleSheet(input_style)
        self.lineEdit_segmento.setPlaceholderText("Ex: restaurant, cafe, gym")

        self.lineEdit_raio = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_raio.setGeometry(QtCore.QRect(480, 82, 100, 28))
        self.lineEdit_raio.setStyleSheet(input_style)
        self.lineEdit_raio.setPlaceholderText("Ex: 5000")
        self.lineEdit_raio.setText("5000")  # Valor padrão

        self.lineEdit_local = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_local.setGeometry(QtCore.QRect(480, 112, 100, 28))
        self.lineEdit_local.setStyleSheet(input_style)
        self.lineEdit_local.setPlaceholderText("Detectando...")
        self.lineEdit_local.setReadOnly(True)

        # ComboBox API
        combo_style = """
            QComboBox {
                background-color: white;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                padding: 5px;
            }
            QComboBox:focus {
                border: 2px solid #3498db;
            }
        """
        
        self.comboBox_api = QtWidgets.QComboBox(Dialog)
        self.comboBox_api.setGeometry(QtCore.QRect(650, 82, 90, 28))
        self.comboBox_api.setStyleSheet(combo_style)
        self.comboBox_api.addItems(["Google", "Yelp", "Foursquare", "OSM"])
        self.comboBox_api.currentTextChanged.connect(self.on_api_changed)

        # Botão Procurar
        self.pushButton_search = QtWidgets.QPushButton("🔍 PROCURAR", Dialog)
        self.pushButton_search.setGeometry(QtCore.QRect(600, 112, 140, 28))
        self.pushButton_search.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.pushButton_search.clicked.connect(self.localizar_empresas)

        # Label de Status
        self.label_status = QtWidgets.QLabel("", Dialog)
        self.label_status.setGeometry(QtCore.QRect(10, 150, 730, 25))
        self.label_status.setStyleSheet("color: #2980b9; font-size: 11px; background: transparent;")
        self.label_status.setAlignment(QtCore.Qt.AlignCenter)

        # TableView
        self.tableView = QtWidgets.QTableView(Dialog)
        self.tableView.setGeometry(QtCore.QRect(10, 185, 730, 400))
        self.tableView.setStyleSheet("""
            QTableView {
                background-color: white;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
            }
            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 5px;
                border: none;
                font-weight: bold;
            }
        """)
        self.tableView.setAlternatingRowColors(True)
        self.tableView.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        # Botão Exportar
        self.pushButton_export = QtWidgets.QPushButton("📊 Exportar para Excel", Dialog)
        self.pushButton_export.setGeometry(QtCore.QRect(520, 595, 220, 35))
        self.pushButton_export.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.pushButton_export.clicked.connect(self.exportar_excel)
        self.pushButton_export.setEnabled(False)

        # Label contador
        self.label_contador = QtWidgets.QLabel("", Dialog)
        self.label_contador.setGeometry(QtCore.QRect(10, 595, 500, 35))
        self.label_contador.setStyleSheet("color: #34495e; font-size: 12px; background: transparent;")
        self.label_contador.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        # Variáveis
        self.empresas = []
        self.latitude = None
        self.longitude = None
        self.busca_thread = None

        # Inicializar localização
        self.definir_localizacao()
        self.on_api_changed()

    def on_api_changed(self):
        """Atualiza placeholder e visibilidade da API Key baseado na API selecionada"""
        api = self.comboBox_api.currentText()
        
        if api == "OSM":
            self.lineEdit_api.setEnabled(False)
            self.lineEdit_api.setPlaceholderText("OSM não requer API Key")
            self.label_api_key.setStyleSheet("color: #95a5a6; font-weight: bold; background: transparent;")
        else:
            self.lineEdit_api.setEnabled(True)
            self.label_api_key.setStyleSheet("color: #34495e; font-weight: bold; background: transparent;")
            
            if api == "Google":
                self.lineEdit_api.setPlaceholderText("Google Places API Key")
                self.lineEdit_segmento.setPlaceholderText("Ex: restaurant, cafe, gym")
            elif api == "Yelp":
                self.lineEdit_api.setPlaceholderText("Yelp API Key (Bearer Token)")
                self.lineEdit_segmento.setPlaceholderText("Ex: pizza, sushi, coffee")
            elif api == "Foursquare":
                self.lineEdit_api.setPlaceholderText("Foursquare API Key")
                self.lineEdit_segmento.setPlaceholderText("Ex: restaurant, bar, hotel")

    def definir_localizacao(self):
        """Obtém a localização automática via IP"""
        self.label_status.setText("⏳ Detectando localização...")
        self.label_status.setStyleSheet("color: #f39c12; font-size: 11px; background: transparent;")
        
        try:
            response = requests.get("http://ip-api.com/json/", timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") == "success":
                self.latitude = data.get("lat")
                self.longitude = data.get("lon")
                cidade = data.get("city", "")
                pais = data.get("country", "")
                
                self.lineEdit_local.setText(f"{cidade}, {pais}")
                self.label_status.setText(f"✓ Localização detectada: {cidade}, {pais}")
                self.label_status.setStyleSheet("color: #27ae60; font-size: 11px; background: transparent;")
            else:
                raise Exception("Falha na detecção")
                
        except Exception as e:
            # Localização padrão: São Paulo
            self.latitude = -23.55052
            self.longitude = -46.633308
            self.lineEdit_local.setText("São Paulo, BR (padrão)")
            self.label_status.setText("⚠ Usando localização padrão: São Paulo")
            self.label_status.setStyleSheet("color: #e67e22; font-size: 11px; background: transparent;")

    def validar_inputs(self):
        """Valida os campos de entrada"""
        api = self.comboBox_api.currentText()
        
        # Valida API Key (exceto para OSM)
        if api != "OSM":
            api_key = self.lineEdit_api.text().strip()
            if not api_key:
                QtWidgets.QMessageBox.warning(
                    None, "Campo Obrigatório", 
                    f"Por favor, informe a API Key para {api}."
                )
                return False
        
        # Valida segmento
        segmento = self.lineEdit_segmento.text().strip()
        if not segmento:
            QtWidgets.QMessageBox.warning(
                None, "Campo Obrigatório", 
                "Por favor, informe o segmento que deseja buscar."
            )
            return False
        
        # Valida raio
        raio = self.lineEdit_raio.text().strip()
        if not raio:
            QtWidgets.QMessageBox.warning(
                None, "Campo Obrigatório", 
                "Por favor, informe o raio de busca em metros."
            )
            return False
        
        try:
            raio_num = int(raio)
            if raio_num <= 0:
                raise ValueError()
            if raio_num > 50000:
                QtWidgets.QMessageBox.warning(
                    None, "Valor Inválido", 
                    "O raio máximo é 50.000 metros (50 km)."
                )
                return False
        except ValueError:
            QtWidgets.QMessageBox.warning(
                None, "Valor Inválido", 
                "O raio deve ser um número inteiro positivo."
            )
            return False
        
        # Valida localização
        if self.latitude is None or self.longitude is None:
            QtWidgets.QMessageBox.warning(
                None, "Erro de Localização", 
                "Não foi possível detectar a localização. Tente novamente."
            )
            return False
        
        return True

    def localizar_empresas(self):
        """Inicia busca de empresas em background"""
        if not self.validar_inputs():
            return
        
        # Desabilita botão durante busca
        self.pushButton_search.setEnabled(False)
        self.pushButton_export.setEnabled(False)
        
        api = self.comboBox_api.currentText()
        api_key = self.lineEdit_api.text().strip()
        raio = self.lineEdit_raio.text().strip()
        segmento = self.lineEdit_segmento.text().strip()
        
        self.label_status.setText(f"🔄 Buscando empresas via {api}... Por favor, aguarde.")
        self.label_status.setStyleSheet("color: #3498db; font-size: 11px; background: transparent;")
        
        # Cria e inicia thread de busca
        self.busca_thread = BuscaThread(api, api_key, raio, segmento, self.latitude, self.longitude)
        self.busca_thread.finalizado.connect(self.on_busca_finalizada)
        self.busca_thread.erro.connect(self.on_busca_erro)
        self.busca_thread.start()

    def on_busca_finalizada(self, empresas, api):
        """Callback quando busca finaliza com sucesso"""
        self.empresas = empresas
        self.pushButton_search.setEnabled(True)
        
        if not empresas:
            self.label_status.setText(f"⚠ Nenhuma empresa encontrada via {api}.")
            self.label_status.setStyleSheet("color: #e67e22; font-size: 11px; background: transparent;")
            self.label_contador.setText("")
            self.pushButton_export.setEnabled(False)
            
            # Limpa tabela
            model = QtGui.QStandardItemModel()
            self.tableView.setModel(model)
            return
        
        # Atualiza status
        self.label_status.setText(f"✓ Busca finalizada com sucesso via {api}!")
        self.label_status.setStyleSheet("color: #27ae60; font-size: 11px; background: transparent;")
        self.label_contador.setText(f"📊 {len(empresas)} empresa(s) encontrada(s)")
        self.pushButton_export.setEnabled(True)
        
        # Atualiza TableView
        model = QtGui.QStandardItemModel()
        model.setHorizontalHeaderLabels(["Nome", "Endereço", "Avaliação", "Reviews", "Latitude", "Longitude"])
        
        for empresa in empresas:
            row = [QtGui.QStandardItem(str(item)) for item in empresa]
            model.appendRow(row)
        
        self.tableView.setModel(model)
        
        # Ajusta largura das colunas
        self.tableView.resizeColumnsToContents()
        self.tableView.horizontalHeader().setStretchLastSection(True)

    def on_busca_erro(self, mensagem_erro):
        """Callback quando busca falha"""
        self.pushButton_search.setEnabled(True)
        self.label_status.setText(f"❌ {mensagem_erro}")
        self.label_status.setStyleSheet("color: #e74c3c; font-size: 11px; background: transparent;")
        
        QtWidgets.QMessageBox.critical(
            None, "Erro na Busca", 
            f"{mensagem_erro}\n\nVerifique:\n"
            "• Sua chave de API está correta\n"
            "• Você tem conexão com a internet\n"
            "• Os parâmetros de busca são válidos"
        )

    def exportar_excel(self):
        """Exporta os dados para arquivo Excel"""
        if not self.empresas:
            QtWidgets.QMessageBox.warning(
                None, "Aviso", 
                "Nenhum dado para exportar. Faça uma busca primeiro."
            )
            return
        
        try:
            # Diálogo para salvar arquivo
            options = QtWidgets.QFileDialog.Options()
            fileName, _ = QtWidgets.QFileDialog.getSaveFileName(
                None,
                "Salvar Arquivo Excel",
                "empresas.xlsx",
                "Excel Files (*.xlsx);;All Files (*)",
                options=options
            )
            
            if fileName:
                if not fileName.endswith('.xlsx'):
                    fileName += '.xlsx'
                
                df = pd.DataFrame(
                    self.empresas, 
                    columns=["Nome", "Endereço", "Avaliação", "Reviews", "Latitude", "Longitude"]
                )
                df.to_excel(fileName, index=False, engine='openpyxl')
                
                QtWidgets.QMessageBox.information(
                    None, "Sucesso", 
                    f"Arquivo exportado com sucesso!\n\n{fileName}"
                )
                self.label_status.setText(f"✓ Exportado: {fileName}")
                self.label_status.setStyleSheet("color: #27ae60; font-size: 11px; background: transparent;")
                
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                None, "Erro ao Exportar", 
                f"Não foi possível exportar o arquivo:\n{str(e)}"
            )


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    
    # Define ícone da janela (se houver)
    # app.setWindowIcon(QtGui.QIcon('icon.png'))
    
    Dialog = QtWidgets.QDialog()
    ui = Ui_Dialog()
    ui.setupUi(Dialog)
    Dialog.show()
    
    sys.exit(app.exec_())
