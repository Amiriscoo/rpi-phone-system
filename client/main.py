import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.error import URLError, HTTPError

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QComboBox, QGridLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget, QMainWindow, QMessageBox, QPushButton, QStackedWidget, QTextEdit, QVBoxLayout, QWidget

from networking.api import Api

ROOT = Path(__file__).resolve().parent

class PhoneWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.api = Api()
        self.setWindowTitle("Pi Phone")
        self.resize(480, 800)
        self.setMinimumSize(480, 520)
        self.setStyleSheet("""
            QWidget { background: #0c1018; color: #e9eef7; font-family: 'DejaVu Sans'; font-size: 15px; }
            QLabel#brand { color: #86d7ff; font-size: 25px; font-weight: 700; }
            QLabel#status { color: #91a0b5; font-size: 12px; }
            QPushButton { background: #182333; border: 1px solid #2d4058; border-radius: 12px; padding: 13px 10px; }
            QPushButton:hover { background: #22334a; }
            QPushButton#primary { background: #27a6c9; color: #071018; font-weight: 700; }
            QPushButton#danger { background: #55273a; }
            QLineEdit, QTextEdit, QComboBox { background: #111a27; border: 1px solid #2b3b51; border-radius: 10px; padding: 10px; }
            QListWidget { background: #111a27; border: 0; border-radius: 12px; padding: 5px; }
            QListWidget::item { padding: 14px; border-bottom: 1px solid #203047; }
            QStackedWidget { background: #0c1018; }
        """)
        self.stack = QStackedWidget()
        self.pages = {}
        for name, builder in [("Home", self.home_page), ("Contacts", self.contacts_page), ("Dialer", self.dialer_page), ("Messages", self.messages_page), ("Settings", self.settings_page), ("JARVIS", self.jarvis_page)]:
            page = builder()
            self.pages[name] = page
            self.stack.addWidget(page)
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(16, 14, 16, 10)
        layout.addWidget(self.top_bar())
        layout.addWidget(self.stack, 1)
        layout.addWidget(self.nav_bar())
        self.setCentralWidget(root)
        self.install_shortcuts()
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_status)
        self.refresh_timer.start(5000)
        self.refresh_status()

    def install_shortcuts(self):
        for key, page in enumerate(["Home", "Contacts", "Dialer", "Messages", "Settings", "JARVIS"], start=1):
            shortcut = QShortcut(QKeySequence(f"Alt+{key}"), self)
            shortcut.activated.connect(lambda page_name=page: self.show_page(page_name))
        escape = QShortcut(QKeySequence("Escape"), self)
        escape.activated.connect(lambda: self.show_page("Home"))

    def top_bar(self):
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 6)
        brand = QLabel("PI PHONE")
        brand.setObjectName("brand")
        layout.addWidget(brand)
        layout.addStretch()
        self.clock = QLabel()
        self.clock.setObjectName("status")
        layout.addWidget(self.clock)
        return bar

    def nav_bar(self):
        bar = QWidget()
        grid = QGridLayout(bar)
        grid.setContentsMargins(0, 8, 0, 0)
        for column, name in enumerate(["Home", "Contacts", "Dialer", "Messages", "Settings", "JARVIS"]):
            button = QPushButton(name)
            button.clicked.connect(lambda checked=False, n=name: self.show_page(n))
            grid.addWidget(button, 0, column)
        return bar

    def show_page(self, name):
        self.stack.setCurrentWidget(self.pages[name])
        if name == "Messages":
            self.load_users()
        if name == "Contacts":
            self.load_contacts()

    def header(self, title, subtitle):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 4, 0, 16)
        label = QLabel(title)
        label.setFont(QFont("DejaVu Sans", 25, QFont.Weight.Bold))
        layout.addWidget(label)
        hint = QLabel(subtitle)
        hint.setObjectName("status")
        layout.addWidget(hint)
        return widget

    def home_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(self.header("Good day.", "Your private Wi-Fi computer is ready."))
        self.connection = QLabel("Checking connection...")
        self.connection.setObjectName("status")
        layout.addWidget(self.connection)
        grid = QGridLayout()
        for index, (name, detail) in enumerate([("Dialer", "Wi-Fi calls"), ("Messages", "Private chat"), ("Contacts", "People"), ("JARVIS", "Assistant"), ("Settings", "Device"), ("Clock", datetime.now().strftime("%H:%M"))]):
            button = QPushButton(f"{name}\n{detail}")
            button.setMinimumHeight(88)
            if name in self.pages:
                button.clicked.connect(lambda checked=False, n=name: self.show_page(n))
            grid.addWidget(button, index // 2, index % 2)
        layout.addLayout(grid)
        layout.addStretch()
        return page

    def contacts_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(self.header("Contacts", "Synced contacts are available when the server is reachable."))
        self.contacts = QListWidget()
        layout.addWidget(self.contacts)
        add = QPushButton("Add local contact")
        add.clicked.connect(self.add_contact)
        layout.addWidget(add)
        return page

    def load_contacts(self):
        self.contacts.clear()
        try:
            contacts = self.api.get("/me").get("contacts", []) if self.api.online else []
        except Exception:
            contacts = []
        for contact in contacts:
            self.contacts.addItem(f"{contact['display_name']}   {contact.get('username') or contact.get('phone') or ''}")
        if not contacts:
            self.contacts.addItem("No synced contacts yet. Add one on the server.")

    def add_contact(self):
        name, ok = self.simple_prompt("Contact name")
        if ok and name:
            try:
                self.api.post("/contacts", {"display_name": name})
                self.load_contacts()
            except Exception as error:
                QMessageBox.information(self, "Offline contact", "The server is unavailable; save this contact locally in Settings when local storage is enabled.")

    def dialer_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(self.header("Dialer", "Wi-Fi calling only. No SIM or cellular radio."))
        self.number = QLineEdit()
        self.number.setPlaceholderText("Username or phone number")
        layout.addWidget(self.number)
        grid = QGridLayout()
        for index, digit in enumerate("123456789*0#"):
            button = QPushButton(digit)
            button.setMinimumHeight(58)
            button.clicked.connect(lambda checked=False, d=digit: self.number.insert(d))
            grid.addWidget(button, index // 3, index % 3)
        layout.addLayout(grid)
        call = QPushButton("Start Wi-Fi call")
        call.setObjectName("primary")
        call.clicked.connect(lambda: QMessageBox.information(self, "Call", "Signaling is ready for in-system calls. Add a SIP/WebRTC media service for audio.") )
        layout.addWidget(call)
        return page

    def messages_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(self.header("Messages", "Server-synced chat with offline-friendly reconnects."))
        self.user_select = QComboBox()
        self.user_select.currentIndexChanged.connect(self.load_messages)
        layout.addWidget(self.user_select)
        self.chat = QListWidget()
        layout.addWidget(self.chat, 1)
        row = QHBoxLayout()
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Write a message")
        send = QPushButton("Send")
        send.setObjectName("primary")
        send.clicked.connect(self.send_message)
        row.addWidget(self.message_input, 1)
        row.addWidget(send)
        layout.addLayout(row)
        return page

    def load_users(self):
        self.user_select.clear()
        if not self.api.online:
            self.user_select.addItem("Offline mode", -1)
            return
        try:
            for user in self.api.get("/users"):
                self.user_select.addItem(user["username"], user["id"])
        except Exception as error:
            self.user_select.addItem(self.api.error_text(error), -1)

    def load_messages(self):
        user_id = self.user_select.currentData()
        self.chat.clear()
        if not user_id or user_id < 0:
            return
        try:
            for message in self.api.get(f"/messages/{user_id}"):
                self.chat.addItem(f"{message['created_at'][11:16]}  {message['body']}")
        except Exception as error:
            self.chat.addItem(self.api.error_text(error))

    def send_message(self):
        recipient = self.user_select.currentData()
        body = self.message_input.text().strip()
        if recipient and recipient > 0 and body:
            try:
                self.api.post(f"/messages/{recipient}", {"body": body})
                self.message_input.clear()
                self.load_messages()
            except URLError:
                self.api.queue_message(recipient, body)
                self.message_input.clear()
                self.chat.addItem("Queued offline. It will send when connected.")
            except Exception as error:
                QMessageBox.warning(self, "Message not sent", self.api.error_text(error))

    def settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(self.header("Settings", "Network, device identity, and local controls."))
        self.server_label = QLabel(f"Server: {self.api.base_url}")
        self.server_label.setObjectName("status")
        layout.addWidget(self.server_label)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password (8+ characters)")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.username_input)
        layout.addWidget(self.password_input)
        auth_row = QHBoxLayout()
        login = QPushButton("Sign in")
        login.setObjectName("primary")
        login.clicked.connect(lambda: self.authenticate(False))
        register = QPushButton("Create account")
        register.clicked.connect(lambda: self.authenticate(True))
        auth_row.addWidget(login)
        auth_row.addWidget(register)
        layout.addLayout(auth_row)
        wifi = QPushButton("Show Wi-Fi networks")
        wifi.clicked.connect(self.show_wifi)
        layout.addWidget(wifi)
        logout = QPushButton("Sign out")
        logout.setObjectName("danger")
        logout.clicked.connect(self.sign_out)
        layout.addWidget(logout)
        layout.addStretch()
        return page

    def show_wifi(self):
        try:
            result = subprocess.check_output(["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi"], text=True, timeout=4)
            QMessageBox.information(self, "Wi-Fi networks", result or "No networks found")
        except Exception:
            QMessageBox.information(self, "Wi-Fi", "NetworkManager is unavailable. Configure Wi-Fi from Raspberry Pi OS settings.")

    def authenticate(self, register):
        try:
            self.api.login(self.username_input.text().strip(), self.password_input.text(), register)
            self.refresh_status()
            QMessageBox.information(self, "Connected", "This device is authenticated with the phone server.")
        except Exception as error:
            QMessageBox.warning(self, "Sign-in failed", self.api.error_text(error))

    def jarvis_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(self.header("JARVIS", "A local-first bridge for your existing assistant."))
        prompt = QTextEdit()
        prompt.setPlaceholderText("Type a prompt for JARVIS")
        layout.addWidget(prompt)
        response = QLabel("JARVIS is ready for your API endpoint.")
        response.setWordWrap(True)
        response.setObjectName("status")
        layout.addWidget(response)
        send = QPushButton("Send prompt")
        send.setObjectName("primary")
        send.clicked.connect(lambda: response.setText("Prompt queued locally. Connect your JARVIS service through the documented API."))
        layout.addWidget(send)
        return page

    def refresh_status(self):
        self.clock.setText(datetime.now().strftime("%H:%M"))
        if not self.api.online:
            self.connection.setText("LOCAL MODE  |  Sign in from Settings to connect")
            self.connection.setStyleSheet("color: #e8b86b")
            return
        try:
            queued = self.api.flush_message_queue()
            health = self.api.get("/health")
            queue_text = f"  |  sent {queued} queued" if queued else ""
            self.connection.setText(f"ONLINE  |  {health['service']}  |  {datetime.now().strftime('%H:%M:%S')}{queue_text}")
            self.connection.setStyleSheet("color: #76e0ae")
        except Exception:
            self.connection.setText("OFFLINE  |  Local apps continue to work")
            self.connection.setStyleSheet("color: #e8b86b")

    def sign_out(self):
        self.api.logout()
        self.refresh_status()
        QMessageBox.information(self, "Signed out", "The device is now in local mode.")

    def simple_prompt(self, title):
        return QInputDialog.getText(self, title, title + ":")

def main():
    app = QApplication(sys.argv)
    window = PhoneWindow()
    if "--fullscreen" in sys.argv:
        window.showFullScreen()
    else:
        window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
