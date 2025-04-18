# main_view.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QMenuBar, QAction, QStackedWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from src.views.transactions.TransactionView import TransactionsView
from src.views.AnalysisView import AnalysisView
from src.views.PredictionsView import PredictionsView
from src.views.SettingsView import SettingsView
from src.views.FAQView import FAQView

class MainView(QWidget):
    def __init__(self, user_name, email, parent=None):
        super().__init__(parent)
        self.user_name = user_name
        self.email = email
        self.setObjectName("MainView")
        self.MAIN_VIEW_STYLESHEET = """
            #MainView {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #3E88EF, stop:1 #8A2BE2);
            }
            QLabel {
                color: white;
                font-size: 14px;
            }
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.15);
                color: white;
                border: none;
                border-bottom: 2px solid rgba(255, 255, 255, 0.5);
                padding: 8px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-bottom: 2px solid #FFD700;
            }
            QLineEdit::placeholder {
                color: rgba(255, 255, 255, 0.7);
            }
            QPushButton {
                background-color: #FFFFFF;
                color: #3E88EF;
                border: none;
                border-radius: 5px;
                padding: 12px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #E0E0E0;
            }
            QCheckBox {
                color: white;
                font-size: 12px;
            }
                
            
}


        """
        self.init_ui()

    def init_ui(self):

        self.setWindowTitle("Budgetify - Főoldal")
        self.setStyleSheet(self.MAIN_VIEW_STYLESHEET)

        self.setFixedSize(1200,800)

        # Dinamikusan méretezhető container
        self.central_container = QWidget(self)
        self.central_container.setObjectName("central_container")

        # Layout az ablakhoz igazított containerhez
        self.container_layout = QVBoxLayout(self.central_container)
        self.container_layout.setAlignment(Qt.AlignCenter)
        self.container_layout.addWidget(self.central_container)

        label = QLabel(f"Üdvözlünk, {self.user_name, self.email}!", self)
        label.setAlignment(Qt.AlignCenter)
        label.setFont(QFont("Arial", 20, QFont.Bold))
        label.setStyleSheet("color: white;")

        menubar = QMenuBar(self)
        menubar.setStyleSheet("""
            QMenuBar {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #3E88EF, stop:1 #8A2BE2);
                font-size: 14px;
            }
            QMenuBar::item {
                background-color: transparent;
                color: white;
                padding: 4px 10px;
            }
            QMenuBar::item:selected, QMenuBar::item:hover  {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
            }
        """)

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

        self.stacked_widget = QStackedWidget()
        self.home_view = label
        self.transactions_view = TransactionsView(self.email, self.central_container)
        self.analysis_view = AnalysisView(self.stacked_widget)
        self.predictions_view = PredictionsView(self.email, self.stacked_widget)
        self.settings_view = SettingsView(self.stacked_widget)
        self.faq_view = FAQView(self.stacked_widget)

        for view in [self.home_view, self.transactions_view, self.analysis_view, self.predictions_view,
                     self.settings_view, self.faq_view]:
            if isinstance(view, QLabel):
                view.setAlignment(Qt.AlignCenter)
            self.stacked_widget.addWidget(view)

        home_action.triggered.connect(lambda: self.navigate(0))
        transactions_action.triggered.connect(lambda: self.navigate(1))
        analysis_action.triggered.connect(lambda: self.navigate(2))
        predictions_action.triggered.connect(lambda: self.navigate(3))
        settings_action.triggered.connect(lambda: self.navigate(4))
        faq_action.triggered.connect(lambda: self.navigate(5))

        self.container_layout.addWidget(menubar)
        self.container_layout.addWidget(self.stacked_widget)

        self.setLayout(self.container_layout)

    def navigate(self, index):
        self.stacked_widget.setCurrentIndex(index)