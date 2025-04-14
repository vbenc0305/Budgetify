from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QPushButton, QDialog, QListWidgetItem, \
    QSizePolicy, QTableWidgetItem

from src.DAO.DAOimpl import FirebaseDAO
from src.views.transactions.NewTransactionView import NewTransactionView

class TransactionsView(QWidget):
    def __init__(self, email, parent=None):
        super().__init__(parent)
        self.email = email
        self.setObjectName("TransactionsView")
        self.init_ui()

    def init_ui(self):
        from PyQt5.QtGui import QGuiApplication

        self.resize(1000, 1000)


        central_layout = QVBoxLayout(self)

        self.no_transactions_label = QLabel("No transactions found.", self)
        self.no_transactions_label.setAlignment(Qt.AlignCenter)
        self.no_transactions_label.setStyleSheet("color: white;")
        self.no_transactions_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.no_transactions_label.setMargin(10)
        central_layout.addWidget(self.no_transactions_label)
        self.no_transactions_label.hide()

        from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem

        self.list_widget = QTableWidget(self)
        self.list_widget.setColumnCount(6)  # Set the number of columns
        self.list_widget.setHorizontalHeaderLabels(
            ['Amount', 'Category', 'Date', 'Description', 'For', 'Type'])  # Set the column headers
        self.list_widget.setFixedHeight(200)
        self.list_widget.setStyleSheet("border: 1px solid #ccc;")
        central_layout.addWidget(self.list_widget)
        self.list_widget.hide()

        self.add_button = QPushButton("Add new Transaction", self)
        self.add_button.clicked.connect(self.open_new_transaction_view)
        central_layout.addWidget(self.add_button, alignment=Qt.AlignCenter)

        self.load_transactions()

        css = """
        
         #TransactionsView QTableWidget {
            background-color: #2b2b2b;
            color: #ffffff;
            border: 1px solid #444444;
            border-radius: 8px;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            font-size: 14px;
        }
        
        #TransactionsView QTableWidget::item {
            padding: 10px;
            border-bottom: 1px solid #444444;
        }
        
        #TransactionsView QTableWidget::item:selected {
            background-color: #3e88ef;
            color: #ffffff;
        }
        
        #TransactionsView QTableWidget::item:hover {
            background-color: #3e88ef;
            color: #ffffff;
        }
        
        #TransactionsView QTableWidget QHeaderView::section {
            background-color: #3e88ef;
            color: #ffffff;
            padding: 10px;
            border: 1px solid #444444;
            border-radius: 8px;
        }
        
        #TransactionsView QTableWidget QHeaderView::section:horizontal {
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
        }
        
        #TransactionsView QTableWidget QHeaderView::section:vertical {
            border-top-left-radius: 8px;
            border-bottom-left-radius: 8px;
        }
        
        
        #TransactionsView {
            background-color: #f5f5f5;
            font-family: Arial, sans-serif;
            font-size: 14px;
        }
        #TransactionsView QLabel {
            color: #333;
            margin-bottom: 5px;
        }
        #TransactionsView QListWidget, #TransactionsView QPushButton {
            padding: 8px;
            border: 1px solid #ccc;
            border-radius: 4px;
            margin-bottom: 15px;
        }
       #TransactionsView QPushButton {
            padding: 10px 15px; /* Egyenletesebb belső térköz */
            margin: 20px auto; /* Automatikus középre igazítás */
            max-width: 200px; /* Méret korlátozása, hogy ne lógjon ki */
            display: block; /* Blokk elemként viselkedik, így jobban illeszkedik */
        }

        }
        #TransactionsView QPushButton:hover {
            background-color: #45a049;
        }
        """
        self.setStyleSheet(css)

    def load_transactions(self):
        print("Loading transactions for email:", self.email)
        dao = FirebaseDAO('user')  # A 'users' kollekciót adjuk át, mivel a tranzakciók ott vannak
        transactions = dao.read_user_transactions(self.email)  # Az emailt átadjuk a read_user_transactions metódusnak
        print("Transactions fetched:", transactions)

        self.list_widget.clear()
        self.list_widget.setHorizontalHeaderLabels(
            ['Amount', 'Category', 'Date', 'Description', 'For', 'Type'])  # Set the column headers

        if transactions:
            self.no_transactions_label.hide()
            self.list_widget.show()
            for i, transaction in enumerate(transactions):
                self.list_widget.insertRow(i)
                self.list_widget.setItem(i, 0, QTableWidgetItem(str(transaction['amount'])))  # Összeg
                self.list_widget.setItem(i, 1, QTableWidgetItem(transaction['category']))  # Kategória
                self.list_widget.setItem(i, 2, QTableWidgetItem(transaction['date']))  # Dátum
                self.list_widget.setItem(i, 3, QTableWidgetItem(transaction['description']))  # Leírás
                self.list_widget.setItem(i, 4, QTableWidgetItem(transaction['for_who']))  # Kinek
                self.list_widget.setItem(i, 5, QTableWidgetItem(transaction['tran_type']))  # Típus

        else:
            print("No transactions found.")
            self.no_transactions_label.show()
            self.list_widget.hide()

    def open_new_transaction_view(self):
        self.new_transaction_dialog = QDialog(self)
        self.new_transaction_view = NewTransactionView(self.new_transaction_dialog, self.email)
        self.new_transaction_dialog.setWindowTitle("Add New Transaction")
        self.new_transaction_dialog.setLayout(QVBoxLayout())
        self.new_transaction_dialog.layout().addWidget(self.new_transaction_view)
        self.new_transaction_dialog.exec_()