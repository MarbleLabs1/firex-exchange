# -*- coding: utf-8 -*-
# C:\Users\Work\Desktop\DEX SOL MARBL\cosmic_wallet_gui.py
import sys
import time
import json
import threading
import queue
import sqlite3
import secrets
import hashlib
import hmac
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QPushButton, QTextEdit, QWidget,
    QLineEdit, QLabel, QComboBox, QMessageBox, QTabWidget, QInputDialog
)
from PyQt6.QtCore import Qt, QTimer
from cosmic_blockchain import CosmicBlockchain, CosmicAccount
from p2p_network import P2PNetwork
from decimal import Decimal

# Lista simplificada de palavras BIP-39 (2048 palavras reais seriam ideais)
BIP39_WORDS = [
    "abandon", "ability", "able", "about", "above", "absent", "absorb", "abstract",
    "absurd", "abuse", "access", "accident", "account", "accuse", "achieve", "acid",
    # Adicione mais palavras ou use uma lista completa de um arquivo externo
] * 128  # Repetindo para simular 2048 palavras

class CosmicWalletGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cosmic Wallet - Galactic Interface")
        self.network = P2PNetwork(host="127.0.0.1", base_port=5555)
        self.blockchain = CosmicBlockchain(self.network)
        self.accounts = {}
        self.current_account = None
        self.init_ui()  # Inicializa a UI primeiro
        self.load_accounts()  # Carrega contas depois
        self.start_sync()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        tabs = QTabWidget()
        main_layout.addWidget(tabs)

        # Tab Wallet
        wallet_widget = QWidget()
        wallet_layout = QVBoxLayout(wallet_widget)
        self.wallet_combo = QComboBox()
        self.wallet_combo.currentTextChanged.connect(self.select_account)
        wallet_layout.addWidget(self.wallet_combo)
        create_btn = QPushButton("Create Wallet", clicked=self.create_account)
        wallet_layout.addWidget(create_btn)
        import_btn = QPushButton("Import Wallet", clicked=self.import_account)
        wallet_layout.addWidget(import_btn)
        self.address_label = QLabel("Address: N/A")
        wallet_layout.addWidget(self.address_label)
        self.energy_label = QLabel("ENERGY: 0 MC")
        wallet_layout.addWidget(self.energy_label)
        self.cecle_label = QLabel("CECLE: 0 ST")
        wallet_layout.addWidget(self.cecle_label)
        tabs.addTab(wallet_widget, "Wallet")

        # Tab Transfer
        transfer_widget = QWidget()
        transfer_layout = QVBoxLayout(transfer_widget)
        self.recipient_input = QLineEdit("Recipient Address")
        transfer_layout.addWidget(self.recipient_input)
        self.amount_input = QLineEdit("Amount")
        transfer_layout.addWidget(self.amount_input)
        self.token_combo = QComboBox()
        self.token_combo.addItems(["ENERGY", "5vmiteBPb7SYj4s1HmNFbb3kWSuaUu4waENx4vSQDmbs"])
        transfer_layout.addWidget(self.token_combo)
        transfer_btn = QPushButton("Transfer", clicked=self.transfer)
        transfer_layout.addWidget(transfer_btn)
        tabs.addTab(transfer_widget, "Transfer")

        # Tab Mint
        mint_widget = QWidget()
        mint_layout = QVBoxLayout(mint_widget)
        self.mint_amount_input = QLineEdit("Amount to Mint")
        mint_layout.addWidget(self.mint_amount_input)
        self.mint_token_combo = QComboBox()
        self.mint_token_combo.addItems(["ENERGY", "5vmiteBPb7SYj4s1HmNFbb3kWSuaUu4waENx4vSQDmbs"])
        mint_layout.addWidget(self.mint_token_combo)
        mint_btn = QPushButton("Mint Tokens", clicked=self.mint_tokens)
        mint_layout.addWidget(mint_btn)
        tabs.addTab(mint_widget, "Mint")

        # Tab Stake
        stake_widget = QWidget()
        stake_layout = QVBoxLayout(stake_widget)
        self.stake_amount_input = QLineEdit("Amount to Stake")
        stake_layout.addWidget(self.stake_amount_input)
        stake_btn = QPushButton("Stake", clicked=self.stake)
        unstake_btn = QPushButton("Unstake", clicked=self.unstake)
        stake_layout.addWidget(stake_btn)
        stake_layout.addWidget(unstake_btn)
        self.stake_label = QLabel("Staked: 0")
        stake_layout.addWidget(self.stake_label)
        tabs.addTab(stake_widget, "Stake")

        # Tab Status
        status_widget = QWidget()
        status_layout = QVBoxLayout(status_widget)
        self.height_label = QLabel("Height: 0")
        self.pending_label = QLabel("Pending Txs: 0")
        self.validators_label = QLabel("Validators: 0")
        status_layout.addWidget(self.height_label)
        status_layout.addWidget(self.pending_label)
        status_layout.addWidget(self.validators_label)
        tabs.addTab(status_widget, "Status")

        # Log Area
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        main_layout.addWidget(self.log_area)

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(2000)

        self.setStyleSheet("""
            QMainWindow { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #001f3f, stop:1 #004d40); }
            QWidget { color: #e0f7fa; }
            QTabWidget::pane { border: 1px solid #00ffcc; background: rgba(0, 51, 102, 0.85); border-radius: 10px; }
            QTabBar::tab { background: #00bcd4; color: #001f3f; padding: 8px; border-radius: 5px; }
            QTabBar::tab:selected { background: #00ffcc; }
            QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00ffcc, stop:1 #00bcd4); color: #001f3f; border: none; padding: 10px; border-radius: 8px; }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00ffcc, stop:1 #00796b); }
            QLineEdit, QComboBox { background: rgba(0, 31, 63, 0.5); border: 1px solid #00ffcc; padding: 5px; border-radius: 8px; color: #e0f7fa; }
            QTextEdit { background: rgba(0, 77, 64, 0.2); border: 1px solid #00ffcc; border-radius: 5px; }
            QLabel { color: #80deea; }
        """)

    def log(self, message):
        self.log_area.append(f"[Log] {message}")

    def generate_mnemonic(self):
        return " ".join(secrets.choice(BIP39_WORDS) for _ in range(12))

    def mnemonic_to_private_key(self, mnemonic):
        seed = hashlib.pbkdf2_hmac("sha512", mnemonic.encode("utf-8"), b"cosmic wallet", 2048)
        return seed[:32]

    def load_accounts(self):
        try:
            with open("wallets.json", "r") as f:
                for line in f:
                    data = json.loads(line.strip())
                    if "mnemonic" in data:
                        private_key = self.mnemonic_to_private_key(data["mnemonic"])
                        account = CosmicAccount(private_key)
                        self.accounts[account.address] = account
                        self.blockchain.accounts[account.address] = account
                        self.wallet_combo.addItem(f"{account.address[:10]}...", account.address)
                    elif "private_key" in data:
                        account = CosmicAccount(bytes.fromhex(data["private_key"]))
                        self.accounts[account.address] = account
                        self.blockchain.accounts[account.address] = account
                        self.wallet_combo.addItem(f"{account.address[:10]}...", account.address)
        except FileNotFoundError:
            self.log("No wallets.json found, starting fresh.")
        conn = sqlite3.connect(self.blockchain.db_path, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT account FROM balances GROUP BY account")
        for row in cursor.fetchall():
            address = row[0]
            if address not in self.accounts:
                self.log(f"Found address {address} in DB but no mnemonic/private key available.")
        conn.close()

    def save_wallet(self, account, mnemonic=None):
        with open("wallets.json", "a") as f:
            if mnemonic:
                json.dump({"address": account.address, "mnemonic": mnemonic}, f)
            else:
                json.dump({"address": account.address, "private_key": account.private_key.hex()}, f)
            f.write("\n")

    def update_ui(self):
        if self.current_account and self.current_account in self.accounts:
            account = self.accounts[self.current_account]
            self.address_label.setText(f"Address: {self.current_account[:10]}...")
            self.energy_label.setText(f"ENERGY: {account.get_balance('ENERGY', self.blockchain.db_path)} MC")
            self.cecle_label.setText(f"CECLE: {account.get_balance('5vmiteBPb7SYj4s1HmNFbb3kWSuaUu4waENx4vSQDmbs', self.blockchain.db_path)} ST")
            self.stake_label.setText(f"Staked: {account.stake}")
        self.height_label.setText(f"Height: {len(self.blockchain.chain)}")
        self.pending_label.setText(f"Pending Txs: {len(self.blockchain.pending_transactions)}")
        self.validators_label.setText(f"Validators: {len(self.blockchain.validator_pool)}")

    def select_account(self, address):
        self.current_account = address if address in self.accounts else None
        self.update_ui()

    def create_account(self):
        mnemonic = self.generate_mnemonic()
        private_key = self.mnemonic_to_private_key(mnemonic)
        account = self.blockchain.register_account(private_key)
        self.accounts[account.address] = account
        self.save_wallet(account, mnemonic)
        self.wallet_combo.addItem(f"{account.address[:10]}...", account.address)
        self.current_account = account.address
        self.wallet_combo.setCurrentText(f"{account.address[:10]}...")
        self.log(f"Created wallet: {account.address}\nMnemonic: {mnemonic} (save this securely!)")

    def import_account(self):
        mnemonic, ok = QInputDialog.getText(self, "Import Wallet", "Enter 12-word Mnemonic:")
        if ok and mnemonic:
            try:
                private_key = self.mnemonic_to_private_key(mnemonic)
                account = CosmicAccount(private_key)
                if account.address not in self.accounts:
                    self.accounts[account.address] = account
                    self.blockchain.accounts[account.address] = account
                    self.wallet_combo.addItem(f"{account.address[:10]}...", account.address)
                    self.save_wallet(account, mnemonic)
                self.current_account = account.address
                self.wallet_combo.setCurrentText(f"{account.address[:10]}...")
                self.log(f"Imported wallet: {account.address}")
            except ValueError:
                QMessageBox.warning(self, "Error", "Invalid mnemonic!")

    def mint_tokens(self):
        if not self.current_account:
            QMessageBox.warning(self, "Error", "Select a wallet first!")
            return
        amount = self.mint_amount_input.text()
        token = self.mint_token_combo.currentText()
        try:
            amount = Decimal(amount)
            account = self.accounts[self.current_account]
            account.update_balance(token, amount, self.blockchain.db_path)
            self.log(f"Minted {amount} {token} to {self.current_account}")
        except ValueError:
            QMessageBox.warning(self, "Error", "Invalid amount!")

    def transfer(self):
        if not self.current_account:
            QMessageBox.warning(self, "Error", "Select a wallet first!")
            return
        recipient = self.recipient_input.text()
        amount = self.amount_input.text()
        token = self.token_combo.currentText()
        try:
            amount = Decimal(amount)
            sender = self.accounts[self.current_account]
            if sender.get_balance(token, self.blockchain.db_path) < amount + self.blockchain.min_fee:
                self.log(f"Insufficient balance for {amount} {token} + fee")
                return
            tx_data = {
                "sender": self.current_account,
                "recipient": recipient,
                "amount": float(amount),
                "token": token,
                "timestamp": time.time()
            }
            signature = sender.sign(tx_data)
            success, message = self.blockchain.add_transaction("transfer", tx_data, signature, self.current_account)
            self.network.send_message({"type": "transfer", "data": tx_data, "signature": signature})
            self.log(f"Transfer: {message}")
        except ValueError:
            QMessageBox.warning(self, "Error", "Invalid amount!")

    def stake(self):
        if not self.current_account:
            QMessageBox.warning(self, "Error", "Select a wallet first!")
            return
        amount = self.stake_amount_input.text()
        try:
            amount = Decimal(amount)
            account = self.accounts[self.current_account]
            success, message = account.stake_tokens(amount, self.blockchain.db_path)
            self.log(f"Stake: {message}")
        except ValueError:
            QMessageBox.warning(self, "Error", "Invalid amount!")

    def unstake(self):
        if not self.current_account:
            QMessageBox.warning(self, "Error", "Select a wallet first!")
            return
        amount = self.stake_amount_input.text()
        try:
            amount = Decimal(amount)
            account = self.accounts[self.current_account]
            success, message = account.unstake_tokens(amount, self.blockchain.db_path)
            self.log(f"Unstake: {message}")
        except ValueError:
            QMessageBox.warning(self, "Error", "Invalid amount!")

    def start_sync(self):
        def sync():
            while True:
                try:
                    msg, addr = self.network.message_queue.get_nowait()
                    if msg["type"] == "transfer":
                        self.blockchain.pending_transactions.append(msg)
                        self.log(f"Received transfer from {addr}: {msg['data']}")
                except queue.Empty:
                    time.sleep(0.1)
        threading.Thread(target=sync, daemon=True).start()

    def closeEvent(self, event):
        self.network.stop()
        self.update_timer.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    wallet = CosmicWalletGUI()
    wallet.show()
    sys.exit(app.exec())