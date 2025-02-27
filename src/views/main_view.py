from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QMenuBar, QAction, QStackedWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from src.views.TransactionView import TransactionsView
from src.views.AnalysisView import AnalysisView
from src.views.PredictionsView import PredictionsView
from src.views.SettingsView import SettingsView
from src.views.FAQView import FAQView


class MainView(QWidget):
    def __init__(self, user_name, parent=None):
        super().__init__(parent)
        self.user_name = user_name
        self.init_ui()

    def init_ui(self):
        """UI komponens létrehozása modern felső menüsávval és lapváltással."""
        self.setWindowTitle("Budgetify - Főoldal")
        self.setGeometry(100, 100, 600, 400)
        self.setStyleSheet("background-color: #f5f5f5;")

        # Üdvözlő szöveg
        label = QLabel(f"Üdvözlünk, {self.user_name}!", self)
        label.setAlignment(Qt.AlignCenter)
        label.setFont(QFont("Arial", 20, QFont.Bold))
        label.setStyleSheet("color: #333;")

        # Menüsáv létrehozása
        menubar = QMenuBar(self)
        menubar.setStyleSheet("background-color: #4CAF50; color: white; font-size: 14px;")

        home_action = QAction("🏠 Kezdőlap", self)
        transactions_action = QAction("💰 Tranzakciók", self)
        analysis_action = QAction("📊 Elemzés", self)
        predictions_action = QAction("🔮 Predikciók", self)
        settings_action = QAction("⚙️ Beállítások", self)
        faq_action = QAction("❓ FAQ", self)

        menubar.addAction(home_action)
        menubar.addAction(transactions_action)
        menubar.addAction(analysis_action)
        menubar.addAction(predictions_action)
        menubar.addAction(settings_action)
        menubar.addAction(faq_action)

        # Oldalváltás kezelése
        self.stacked_widget = QStackedWidget()
        self.home_view = QLabel("🏠 Kezdőlap")
        self.transactions_view = TransactionsView(self.stacked_widget)
        self.analysis_view = AnalysisView(self.stacked_widget)
        self.predictions_view = PredictionsView(self.stacked_widget)
        self.settings_view = SettingsView(self.stacked_widget)
        self.faq_view = FAQView(self.stacked_widget)

        # Csak a QLabel widgeteknél állítjuk be az igazítást
        for view in [self.home_view, self.transactions_view, self.analysis_view, self.predictions_view,
                     self.settings_view, self.faq_view]:
            if isinstance(view, QLabel):
                view.setAlignment(Qt.AlignCenter)
            self.stacked_widget.addWidget(view)

        # Kattintáskezelés
        home_action.triggered.connect(lambda: self.navigate(0))
        transactions_action.triggered.connect(lambda: self.navigate(1))
        analysis_action.triggered.connect(lambda: self.navigate(2))
        predictions_action.triggered.connect(lambda: self.navigate(3))
        settings_action.triggered.connect(lambda: self.navigate(4))
        faq_action.triggered.connect(lambda: self.navigate(5))

        # Fő layout
        layout = QVBoxLayout(self)
        layout.setMenuBar(menubar)
        layout.addWidget(self.stacked_widget)

        self.setLayout(layout)

    def navigate(self, index):
        """Navigálás a kiválasztott oldalra."""
        self.stacked_widget.setCurrentIndex(index)
