from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QDateTimeEdit, QComboBox
from PyQt5.QtCore import QDateTime

from src.DAO.DAOimpl import FirebaseDAO


class NewTransactionView(QWidget):
    def __init__(self, parent=None, email=None):
        super().__init__(parent)
        self.firebase_dao = FirebaseDAO("transactions")
        self.setObjectName("NewTransactionView")
        self.email=email
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Central container
        central_container = QWidget(self)
        central_container.setObjectName("central_container")
        central_layout = QVBoxLayout(central_container)

        # CSS Styles
        css = """
                #NewTransactionView {
                    background-color: white;
                    font-family: Arial, sans-serif;
                    font-size: 14px;
                }
                #NewTransactionView QLabel {
                    color: #333;
                    margin-bottom: 5px;
                }
                #NewTransactionView QLineEdit, #NewTransactionView QComboBox, #NewTransactionView QDateTimeEdit {
                    padding: 8px;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    margin-bottom: 15px;
                    color: #000;
                }
                #NewTransactionView QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    padding: 10px 20px;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                }
                #NewTransactionView QPushButton:hover {
                    background-color: #45a049;
                }
                #central_container {
                    background-color: rgba(255, 255, 255, 0.2);
                    border-radius: 15px;
                    padding: 20px;
                    backdrop-filter: blur(10px);
                }
                """
        self.setStyleSheet(css)


        # Amount
        self.amount_label = QLabel("Amount:")
        self.amount_input = QLineEdit()
        self.amount_input.setValidator(QIntValidator())  # Only accept numbers
        central_layout.addWidget(self.amount_label)
        central_layout.addWidget(self.amount_input)

        # Category
        self.category_label = QLabel("Category:")
        self.category_input = QComboBox()
        categories = [
            "Számlák, rezsi", "Vendéglátás", "Bevásárlás", "Készpénzfelvétel",
            "Szórakozás", "Egyéb", "Egészség, szépség", "Otthon",
            "Közlekedés", "Adomány", "Ruházat"
        ]
        self.category_input.addItems(categories)
        central_layout.addWidget(self.category_label)
        central_layout.addWidget(self.category_input)

        # Date
        self.date_label = QLabel("Date:")
        self.date_input = QDateTimeEdit(QDateTime.currentDateTime())
        self.date_input.setCalendarPopup(True)
        central_layout.addWidget(self.date_label)
        central_layout.addWidget(self.date_input)

        # Description
        self.description_label = QLabel("Description:")
        self.description_input = QLineEdit()
        central_layout.addWidget(self.description_label)
        central_layout.addWidget(self.description_input)

        # For Who
        self.for_who_label = QLabel("For Who:")
        self.for_who_input = QLineEdit()
        central_layout.addWidget(self.for_who_label)
        central_layout.addWidget(self.for_who_input)

        # Transaction Type
        self.tran_type_label = QLabel("Transaction Type:")
        self.tran_type_input = QComboBox()
        self.tran_type_input.addItems(["outgoing", "incoming"])
        central_layout.addWidget(self.tran_type_label)
        central_layout.addWidget(self.tran_type_input)

        # Submit Button
        self.submit_button = QPushButton("Add Transaction")
        self.submit_button.clicked.connect(self.add_transaction)
        central_layout.addWidget(self.submit_button)

        layout.addWidget(central_container)
        self.setLayout(layout)

    def add_transaction(self):
        # Az űrlap mezőiből adatgyűjtés
        data = {
            "amount": self.amount_input.text(),
            "category": self.category_input.currentText(),
            # A QDateTimeEdit-ből érdemes a dateTime() metódust használni a megfelelő formázás érdekében:
            "date": self.date_input.dateTime().toString("yyyy-MM-dd HH:mm:ss"),
            "description": self.description_input.text(),
            "for_who": self.for_who_input.text(),
            "tran_type": self.tran_type_input.currentText(),
            "email" : self.email,

        }

        # Példa: Ha van egy FirebaseDAO példányunk, pl. user_dao, akkor:
        if self.firebase_dao.create(data):
            print("Transaction successfully saved!")
            # Itt frissítheted az UI-t, például törölheted az űrlapot, vagy egy visszajelző üzenetet jeleníthetsz meg.
        else:
            print("Error saving transaction.")
