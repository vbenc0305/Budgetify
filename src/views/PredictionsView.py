from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QMessageBox
from src.DAO.DAOimpl import FirebaseDAO


class FirebaseWorker(QThread):
    data_ready = pyqtSignal(list)

    def __init__(self, firebase_dao, email):
        super().__init__()
        self.firebase_dao = firebase_dao
        self.email = email

    def run(self):
        try:
            # Próbáljuk meg lekérni a tranzakciókat a Firebase-ből
            docs = self.firebase_dao.read_user_transactions(self.email)
            print("docs - " , docs)
            self.data_ready.emit(docs)
        except Exception as e:
            print(f"Hiba történt az adatlekérés során: {e}")
            self.data_ready.emit([])  # Hibás esetben üres listát adunk vissza


class PredictionsView(QWidget):
    def __init__(self, email, parent=None):
        super().__init__(parent)
        self.firebase_dao_user = FirebaseDAO("user")
        self.firebase_dao_trans = FirebaseDAO("transactions")
        self.email = email
        self.init_ui()

    def check_transaction_count(self, docs):
        count = len(docs)
        print("Transaction count:", count)
        if count < 50:
            # Megjelenítünk egy figyelmeztetést, ha a tranzakciók száma kevesebb, mint 50
            QMessageBox.warning(
                self,
                "⚠️ Kevés adat",
                f"Legalább 50 tranzakció szükséges a predikcióhoz.\nJelenleg csak {count} van."
            )
            self.warning_label.setText("⚠️ Kevés adat a predikcióhoz.")
            self.warning_label.setStyleSheet("color: white;")
        else:
            self.warning_label.setText("✅ Elég tranzakció áll rendelkezésre predikcióhoz.")
            self.warning_label.setStyleSheet("color: white;")

    def init_ui(self):
        layout = QVBoxLayout()

        title = QLabel("🔮 Predikciók oldal")
        title.setAlignment(Qt.AlignCenter)

        # Kezdeti üzenet az adatok betöltése közben
        self.warning_label = QLabel("Adatok betöltése...")
        self.warning_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(title)
        layout.addWidget(self.warning_label)
        self.setLayout(layout)

        # Aszinkron adatlekérés indítása a FirebaseWorker segítségével
        self.worker = FirebaseWorker(self.firebase_dao_user, self.email)
        self.worker.data_ready.connect(self.check_transaction_count)
        self.worker.start()
