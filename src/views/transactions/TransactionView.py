from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QDialog,
    QSizePolicy, QTableWidgetItem, QTableWidget, QHeaderView
)
from src.DAO.DAOimpl import FirebaseDAO
from src.views.transactions.NewTransactionView import NewTransactionView


class TransactionsView(QWidget):
    def __init__(self, email, parent=None):
        super().__init__(parent)
        self.email = email
        self.page_size = 50  # Egyszerre betöltendő rekordok száma
        self.current_page = 0  # Jelenlegi oldal (0-index)
        self.all_transactions = []  # Itt tároljuk az összes lekért tranzakciót
        self.setObjectName("TransactionsView")
        self.init_ui()

    def init_ui(self):
        self.resize(1000, 1000)
        central_layout = QVBoxLayout(self)

        self.no_transactions_label = QLabel("No transactions found.", self)
        self.no_transactions_label.setAlignment(Qt.AlignCenter)
        self.no_transactions_label.setStyleSheet("color: white;")
        self.no_transactions_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.no_transactions_label.setMargin(10)
        central_layout.addWidget(self.no_transactions_label)
        self.no_transactions_label.hide()

        # QTableWidget beállítása
        self.list_widget = QTableWidget(self)
        self.list_widget.setColumnCount(6)
        self.list_widget.setHorizontalHeaderLabels(
            ['Amount', 'Category', 'Date', 'Description', 'For', 'Type']
        )
        self.list_widget.setFixedHeight(200)
        self.list_widget.setStyleSheet("border: 1px solid #ccc;")
        # Az oszlopok egyenlő elosztása: Stretch üzemmód minden oszlopra
        header = self.list_widget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        central_layout.addWidget(self.list_widget)
        self.list_widget.hide()

        # Gombok a lapozáshoz: "Előző oldal" és "Következő oldal"
        self.previous_button = QPushButton("Előző oldal", self)
        self.previous_button.clicked.connect(self.load_previous_page)
        self.previous_button.hide()  # Kezdetben a legelső oldalon, így nincs előző oldal
        central_layout.addWidget(self.previous_button, alignment=Qt.AlignCenter)

        self.next_button = QPushButton("Következő oldal", self)
        self.next_button.clicked.connect(self.load_next_page)
        self.next_button.hide()  # Ez akkor lesz látható, ha több oldal is van
        central_layout.addWidget(self.next_button, alignment=Qt.AlignCenter)

        # Új tranzakció felvitele gomb
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
            padding: 10px 15px;
            margin: 20px auto;
            max-width: 200px;
            display: block;
        }
        #TransactionsView QPushButton:hover {
            background-color: #45a049;
        }
        """
        self.setStyleSheet(css)

    def load_transactions(self):
        print("Loading transactions for email:", self.email)
        dao = FirebaseDAO('user')  # A 'user' kollekciót használjuk, ahol a tranzakciók vannak
        transactions = dao.read_user_transactions(self.email)
        print("Transactions fetched:", transactions)

        self.all_transactions = transactions

        self.list_widget.clearContents()
        self.list_widget.setRowCount(0)
        self.list_widget.setHorizontalHeaderLabels(
            ['Amount', 'Category', 'Date', 'Description', 'For', 'Type']
        )

        if transactions:
            self.no_transactions_label.hide()
            self.list_widget.show()
            self.current_page = 0
            self.load_page(self.current_page)
            # Ha több tranzakció van, mint egy oldal mérete, a következő oldal gomb megjelenik
            if len(transactions) > self.page_size:
                self.next_button.show()
            else:
                self.next_button.hide()
            self.previous_button.hide()
        else:
            print("No transactions found.")
            self.no_transactions_label.show()
            self.list_widget.hide()
            self.previous_button.hide()
            self.next_button.hide()

    def load_page(self, page):
        start = page * self.page_size
        end = start + self.page_size
        page_transactions = self.all_transactions[start:end]

        # Tábla ürítése, majd feltöltése az adott oldallal
        self.list_widget.clearContents()
        self.list_widget.setRowCount(0)
        for i, transaction in enumerate(page_transactions):
            self.list_widget.insertRow(i)
            self.list_widget.setItem(i, 0, QTableWidgetItem(str(transaction.get('amount', ''))))
            self.list_widget.setItem(i, 1, QTableWidgetItem(transaction.get('category', '')))
            self.list_widget.setItem(i, 2, QTableWidgetItem(transaction.get('date', '')))
            self.list_widget.setItem(i, 3, QTableWidgetItem(transaction.get('description', '')))
            self.list_widget.setItem(i, 4, QTableWidgetItem(transaction.get('for_who', '')))
            self.list_widget.setItem(i, 5, QTableWidgetItem(transaction.get('tran_type', '')))

        # Gombok állapotának frissítése
        if page == 0:
            self.previous_button.hide()
        else:
            self.previous_button.show()
        if end >= len(self.all_transactions):
            self.next_button.hide()
        else:
            self.next_button.show()

    def load_next_page(self):
        self.current_page += 1
        self.load_page(self.current_page)

    def load_previous_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.load_page(self.current_page)

    def open_new_transaction_view(self):
        self.new_transaction_dialog = QDialog(self)
        self.new_transaction_view = NewTransactionView(self.new_transaction_dialog, self.email)
        self.new_transaction_dialog.setWindowTitle("Add New Transaction")
        self.new_transaction_dialog.setLayout(QVBoxLayout())
        self.new_transaction_dialog.layout().addWidget(self.new_transaction_view)
        self.new_transaction_dialog.exec_()
