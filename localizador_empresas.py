"""Aplicativo desktop para descobrir empresas por proximidade."""
import sys
from PyQt5 import QtCore, QtGui, QtWidgets as W
from servicos import COLUNAS, SEGMENTOS, buscar, coordenadas, detectar_localizacao, salvar_excel

STYLE = """
QWidget { font-family: 'Segoe UI'; font-size: 13px; color: #203b38; }
QDialog { background: #f2f6f5; }
QFrame#card { background: white; border: 1px solid #dde7e3; border-radius: 12px; }
QLabel#title { font-size: 28px; font-weight: 700; color: #123e34; }
QLabel#eyebrow { color: #168069; font-weight: 700; font-size: 11px; }
QLabel#muted { color: #637b76; }
QLabel#section { font-size: 17px; font-weight: 600; }
QLineEdit, QComboBox, QSpinBox { background: white; border: 1px solid #cad9d3; border-radius: 6px; padding: 8px; min-height: 20px; selection-background-color: #126b58; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border: 1px solid #168069; }
QLineEdit:disabled { background: #f1f5f3; color: #7a8c87; }
QPushButton { background: #eaf3ef; border: 1px solid #ccded5; border-radius: 6px; padding: 10px 16px; font-weight: 600; }
QPushButton:hover { background: #dcece4; }
QPushButton#primary { background: #126b58; color: white; border: none; }
QPushButton#primary:hover { background: #0b5343; }
QPushButton:disabled { background: #e5ebe8; color: #8c9c95; border: none; }
QTableView { background: white; alternate-background-color: #f7faf8; border: none; gridline-color: #edf2ef; selection-background-color: #daeee4; selection-color: #134b39; }
QHeaderView::section { background: #edf4f0; color: #4d6961; border: none; border-bottom: 1px solid #dbe6df; padding: 12px 8px; font-weight: 600; }
QProgressBar { border: none; background: #e6efea; max-height: 4px; }
QProgressBar::chunk { background: #168069; }
"""


class Tarefa(QtCore.QThread):
    resultado = QtCore.pyqtSignal(object)
    erro = QtCore.pyqtSignal(str)

    def __init__(self, func, *args):
        super().__init__()
        self.func, self.args = func, args

    def run(self):
        try:
            self.resultado.emit(self.func(*self.args))
        except ValueError as exc:
            self.erro.emit(str(exc))
        except Exception:
            self.erro.emit("Não foi possível concluir a operação. Confira os dados e tente novamente.")


def label(text, name=None):
    widget = W.QLabel(text)
    widget.setTextFormat(QtCore.Qt.PlainText)
    if name:
        widget.setObjectName(name)
    widget.setWordWrap(True)
    return widget


class Janela(W.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Localizador de empresas")
        self.resize(1160, 760)
        self.setMinimumSize(900, 660)
        self.setStyleSheet(STYLE)
        self.tarefa = None
        self.empresas = []
        root = W.QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 20)
        root.setSpacing(16)
        root.addWidget(label("EXPLORAR • CONECTAR • CRESCER", "eyebrow"))
        root.addWidget(label("Encontre empresas ao seu redor", "title"))
        root.addWidget(label("Escolha um segmento e descubra oportunidades na região que você quer explorar.", "muted"))
        body = W.QHBoxLayout()
        body.setSpacing(20)
        root.addLayout(body, 1)
        card = W.QFrame()
        card.setObjectName("card")
        card.setFixedWidth(310)
        side = W.QVBoxLayout(card)
        side.setContentsMargins(20, 20, 20, 20)
        side.setSpacing(10)
        body.addWidget(card)
        side.addWidget(label("Sua busca", "section"))
        side.addWidget(label("01  Fonte dos dados", "muted"))
        self.api = W.QComboBox()
        self.api.addItems(["OSM", "Google", "Yelp", "Foursquare"])
        side.addWidget(self.api)
        self.key = W.QLineEdit()
        self.key.setEchoMode(W.QLineEdit.Password)
        self.key.setAccessibleName("Chave de acesso da API")
        side.addWidget(self.key)
        side.addWidget(label("02  Segmento", "muted"))
        self.segmento = W.QComboBox()
        self.segmento.setEditable(True)
        self.segmento.addItems(SEGMENTOS)
        side.addWidget(self.segmento)
        side.addWidget(label("Raio de busca", "muted"))
        self.raio = W.QSpinBox()
        self.raio.setRange(1, 50000)
        self.raio.setValue(5000)
        self.raio.setSingleStep(1000)
        self.raio.setSuffix(" m")
        side.addWidget(self.raio)
        side.addWidget(label("03  Centro da busca", "muted"))
        coords = W.QHBoxLayout()
        self.lat, self.lon = W.QLineEdit(), W.QLineEdit()
        self.lat.setPlaceholderText("Latitude")
        self.lon.setPlaceholderText("Longitude")
        self.lat.setAccessibleName("Latitude")
        self.lon.setAccessibleName("Longitude")
        coords.addWidget(self.lat)
        coords.addWidget(self.lon)
        side.addLayout(coords)
        self.detectar = W.QPushButton("Usar localização por IP")
        self.detectar.clicked.connect(self.localizar)
        side.addWidget(self.detectar)
        side.addWidget(label("A localização por IP é aproximada. Revise as coordenadas antes de buscar.", "muted"))
        side.addStretch()
        self.search = W.QPushButton("Buscar empresas")
        self.search.setObjectName("primary")
        self.search.clicked.connect(self.pesquisar)
        side.addWidget(self.search)
        results = W.QFrame()
        results.setObjectName("card")
        layout = W.QVBoxLayout(results)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(14)
        body.addWidget(results, 1)
        heading = W.QHBoxLayout()
        heading.addWidget(label("Empresas encontradas", "section"))
        heading.addStretch()
        self.export = W.QPushButton("Exportar Excel")
        self.export.setEnabled(False)
        self.export.clicked.connect(self.exportar)
        heading.addWidget(self.export)
        layout.addLayout(heading)
        self.filtro = W.QLineEdit()
        self.filtro.setPlaceholderText("Filtrar resultados por nome ou endereço…")
        self.filtro.setClearButtonEnabled(True)
        layout.addWidget(self.filtro)
        self.model = QtGui.QStandardItemModel(0, len(COLUNAS), self)
        self.model.setHorizontalHeaderLabels(COLUNAS)
        self.proxy = QtCore.QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.proxy.setFilterKeyColumn(-1)
        self.filtro.textChanged.connect(self.filtrar)
        self.stack = W.QStackedWidget()
        empty = W.QWidget()
        empty_layout = W.QVBoxLayout(empty)
        empty_layout.addStretch()
        self.empty_title = label("Sua próxima oportunidade começa aqui", "section")
        self.empty_detail = label("Defina a localização e clique em Buscar empresas.\nO OpenStreetMap funciona sem chave de acesso.", "muted")
        for item in (self.empty_title, self.empty_detail):
            item.setAlignment(QtCore.Qt.AlignCenter)
            empty_layout.addWidget(item)
        empty_layout.addStretch()
        self.stack.addWidget(empty)
        self.table = W.QTableView()
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.setEditTriggers(W.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(W.QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(46)
        self.table.setColumnWidth(0, 220)
        self.table.setColumnWidth(1, 290)
        self.stack.addWidget(self.table)
        layout.addWidget(self.stack, 1)
        self.contador = label("Nenhuma busca realizada", "muted")
        layout.addWidget(self.contador)
        self.fonte = label("Dados: © colaboradores do OpenStreetMap • ODbL", "muted")
        layout.addWidget(self.fonte)
        self.progresso = W.QProgressBar()
        self.progresso.setRange(0, 0)
        self.progresso.setTextVisible(False)
        self.progresso.hide()
        root.addWidget(self.progresso)
        self.status = label("Pronto para explorar. Informe as coordenadas ou use a localização por IP.", "muted")
        root.addWidget(self.status)
        self.api.currentTextChanged.connect(self.mudar_api)
        self.mudar_api()
        for button in self.findChildren(W.QPushButton):
            button.setAutoDefault(False)

    def mudar_api(self):
        api = self.api.currentText()
        self.key.setEnabled(api != "OSM")
        self.key.setPlaceholderText("Sem chave • acesso público" if api == "OSM" else f"Chave de acesso • {api}")
        self.raio.setMaximum(40000 if api == "Yelp" else 50000)

    def ocupar(self, busy):
        for w in (self.api, self.segmento, self.raio, self.lat, self.lon, self.detectar, self.search):
            w.setEnabled(not busy)
        self.key.setEnabled(not busy and self.api.currentText() != "OSM")
        self.export.setEnabled(not busy and self.proxy.rowCount() > 0)
        self.progresso.setVisible(busy)
        self.search.setText("Aguarde…" if busy else "Buscar empresas")

    def executar(self, func, args, callback, mensagem):
        if self.tarefa is not None:
            return
        self.ocupar(True)
        self.status.setText(mensagem)
        self.tarefa = Tarefa(func, *args)
        self.tarefa.resultado.connect(callback)
        self.tarefa.erro.connect(self.falha)
        self.tarefa.finished.connect(self.terminou)
        self.tarefa.start()

    def terminou(self):
        self.tarefa.deleteLater()
        self.tarefa = None
        self.ocupar(False)

    def falha(self, message):
        self.status.setText(message + (" Os resultados anteriores foram mantidos." if self.empresas else ""))

    def localizar(self):
        self.executar(detectar_localizacao, (), self.localizado, "Detectando localização aproximada por IP…")

    def localizado(self, result):
        lat, lon, city = result
        self.lat.setText(str(lat))
        self.lon.setText(str(lon))
        self.status.setText(f"Localização aproximada: {city}. Revise as coordenadas antes de buscar.")

    def pesquisar(self):
        try:
            lat, lon = coordenadas(self.lat.text(), self.lon.text())
            if not self.segmento.currentText().strip():
                raise ValueError("Escolha ou digite um segmento.")
            if self.api.currentText() != "OSM" and not self.key.text().strip():
                raise ValueError("Informe a chave de acesso do provedor selecionado.")
        except (ValueError, TypeError):
            self.status.setText("Revise os campos: coordenadas válidas, segmento e chave de acesso (exceto OSM).")
            return
        self.api_busca = self.api.currentText()
        self.executar(buscar, (self.api_busca, self.key.text().strip(), self.raio.value(), self.segmento.currentText().strip(), lat, lon), self.resultados, f"Buscando empresas via {self.api_busca}…")

    def resultados(self, rows):
        self.empresas = rows
        self.model.removeRows(0, self.model.rowCount())
        for row in rows:
            items = []
            for value in row:
                item = QtGui.QStandardItem()
                item.setData(value if value is not None else "—", QtCore.Qt.DisplayRole)
                item.setToolTip(str(value) if value is not None else "Não informado pelo provedor")
                items.append(item)
            self.model.appendRow(items)
        self.filtro.clear()
        self.filtrar("")
        self.fonte.setText({"OSM": "Dados: © colaboradores do OpenStreetMap • ODbL", "Google": "Dados: Google Maps • Até 20 resultados por consulta", "Yelp": "Dados: Yelp • Até 50 resultados por consulta", "Foursquare": "Dados: Foursquare • Até 50 resultados por consulta"}[self.api_busca])
        self.status.setText("Busca concluída. A cobertura depende dos dados do provedor.")

    def filtrar(self, text):
        self.proxy.setFilterFixedString(text)
        count = self.proxy.rowCount()
        self.contador.setText(f"{count} de {len(self.empresas)} empresas • exportação dos resultados visíveis")
        self.stack.setCurrentIndex(1 if count else 0)
        if not count:
            self.empty_title.setText("Nenhum resultado para este filtro" if self.empresas else "Nenhuma empresa encontrada")
            self.empty_detail.setText("Experimente outro nome ou limpe o filtro." if self.empresas else "Tente outro segmento, ajuste as coordenadas ou aumente o raio.")
        self.export.setEnabled(count > 0 and self.tarefa is None)

    def exportar(self):
        path, _ = W.QFileDialog.getSaveFileName(self, "Exportar resultados visíveis", "empresas.xlsx", "Planilha Excel (*.xlsx)")
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        rows = [self.empresas[self.proxy.mapToSource(self.proxy.index(r, 0)).row()] for r in range(self.proxy.rowCount())]
        self.executar(salvar_excel, (path, rows), lambda _: self.status.setText(f"Planilha salva: {path}"), "Preparando planilha Excel…")

    def closeEvent(self, event):
        if self.tarefa is not None:
            self.status.setText("Aguarde a operação terminar antes de fechar a janela.")
            event.ignore()
        else:
            event.accept()


if __name__ == "__main__":
    W.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
    app = W.QApplication(sys.argv)
    app.setStyle("Fusion")
    janela = Janela()
    janela.show()
    sys.exit(app.exec_())
