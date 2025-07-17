# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QWidget,
    QLineEdit, QLabel, QMessageBox, QTabWidget
)
from PyQt6.QtCore import Qt, QTimer
import sys
import threading
import psutil
from cosmic_blockchain import CosmicBlockchain, CosmicBlock
from smartcontract import CosmicDEX
from p2p_network import P2PNetwork
from solana_bridge import SolanaBridge
from POS_offgrid_ai import OffGridAI

class GalacticDEXGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Galactic DEX - Off-Grid")
        self.network = P2PNetwork()
        self.blockchain = CosmicBlockchain(self.network)
        self.dex = CosmicDEX(self.blockchain)
        self.bridge = SolanaBridge(self.blockchain, self.dex)
        self.ai = OffGridAI(self.blockchain)
        self.explorer = self.blockchain.register_account()
        self.explorer_id = self.explorer.address
        energy = self.dex.register_token("ENERGY", "Cosmic Energy", "MC", 6)
        star = self.dex.register_token("STAR", "Stardust", "ST", 6)
        self.pool = self.dex.create_pool("ENERGY", "STAR")
        self.explorer.add_balance("ENERGY", 1000)
        self.explorer.add_balance("STAR", 500)
        self.exploring = False
        self.exploration_threads = []
        self.planets_discovered = 0
        self.init_ui()
        self.start_network_sync()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        tabs = QTabWidget()
        main_layout.addWidget(tabs)

        # Tab Wallet
        wallet_widget = QWidget()
        wallet_layout = QVBoxLayout(wallet_widget)
        self.balance_label = QLabel(f"ENERGY: {self.explorer.get_balance('ENERGY')} MC | STAR: {self.explorer.get_balance('STAR')} ST")
        wallet_layout.addWidget(self.balance_label)
        transfer_layout = QHBoxLayout()
        self.dest_input = QLineEdit("Destino")
        transfer_layout.addWidget(self.dest_input)
        self.amount_input = QLineEdit("Quantidade")
        transfer_layout.addWidget(self.amount_input)
        send_btn = QPushButton("Transferir ENERGY", clicked=self.transfer_energy)
        transfer_layout.addWidget(send_btn)
        wallet_layout.addLayout(transfer_layout)
        tabs.addTab(wallet_widget, "Carteira")

        # Tab Mining
        mining_widget = QWidget()
        mining_layout = QVBoxLayout(mining_widget)
        self.start_btn = QPushButton("Iniciar Mineração", clicked=self.start_mining)
        mining_layout.addWidget(self.start_btn)
        self.stop_btn = QPushButton("Parar Mineração", clicked=self.stop_mining)
        self.stop_btn.hide()
        mining_layout.addWidget(self.stop_btn)
        self.planets_label = QLabel("Planetas: 0")
        mining_layout.addWidget(self.planets_label)
        tabs.addTab(mining_widget, "Mineração")

        # Tab DEX
        dex_widget = QWidget()
        dex_layout = QVBoxLayout(dex_widget)
        self.swap_input = QLineEdit("Quantidade ENERGY")
        dex_layout.addWidget(self.swap_input)
        swap_btn = QPushButton("Swap ENERGY -> STAR", clicked=self.swap)
        dex_layout.addWidget(swap_btn)
        self.liq_a_input = QLineEdit("ENERGY")
        self.liq_b_input = QLineEdit("STAR")
        dex_layout.addWidget(self.liq_a_input)
        dex_layout.addWidget(self.liq_b_input)
        add_liq_btn = QPushButton("Adicionar Liquidez", clicked=self.add_liquidity)
        dex_layout.addWidget(add_liq_btn)
        self.pool_label = QLabel(f"Pool: ENERGY: {self.pool.reserve_a} | STAR: {self.pool.reserve_b}")
        dex_layout.addWidget(self.pool_label)
        tabs.addTab(dex_widget, "DEX")

        # Tab Bridge
        bridge_widget = QWidget()
        bridge_layout = QVBoxLayout(bridge_widget)
        self.bridge_amount = QLineEdit("Quantidade ENERGY")
        bridge_layout.addWidget(self.bridge_amount)
        lock_btn = QPushButton("Lock para Solana", clicked=self.lock_to_solana)
        bridge_layout.addWidget(lock_btn)
        tabs.addTab(bridge_widget, "Ponte Solana")

        # Log
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        main_layout.addWidget(self.log_area)

        # Timers
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(1000)
        self.ai_timer = QTimer()
        self.ai_timer.timeout.connect(self.ai.enforce_rules)
        self.ai_timer.start(500)  # Verificação constante

    def log(self, message):
        self.log_area.append(f"[Log] {message}")

    def update_ui(self):
        self.balance_label.setText(f"ENERGY: {self.explorer.get_balance('ENERGY')} MC | STAR: {self.explorer.get_balance('STAR')} ST")
        self.pool_label.setText(f"Pool: ENERGY: {self.pool.reserve_a} | STAR: {self.pool.reserve_b}")

    def transfer_energy(self):
        dest = self.dest_input.text()
        amount = float(self.amount_input.text())
        tx_data = {"sender": self.explorer_id, "recipient": dest, "amount": amount}
        signature = self.explorer.sign(tx_data)
        self.blockchain.add_transaction("transfer", tx_data, signature)
        self.log(f"Transferindo {amount} ENERGY para {dest}")

    def start_mining(self):
        if not self.exploring:
            self.exploring = True
            self.start_btn.hide()
            self.stop_btn.show()
            for _ in range(psutil.cpu_count()):
                thread = threading.Thread(target=self.mine, daemon=True)
                self.exploration_threads.append(thread)
                thread.start()

    def stop_mining(self):
        self.exploring = False
        for thread in self.exploration_threads:
            if thread.is_alive():
                thread.join()
        self.exploration_threads.clear()
        self.start_btn.show()
        self.stop_btn.hide()

    def mine(self):
        while self.exploring:
            if self.ai.validate_mining(self.explorer_id):
                self.planets_discovered += 1
                self.planets_label.setText(f"Planetas: {self.planets_discovered}")
                self.log("Bloco minerado com validação da IA!")

    def swap(self):
        amount = float(self.swap_input.text())
        tx_data = {"account": self.explorer_id, "pool_id": self.pool.pool_id, "amount": amount}
        signature = self.explorer.sign(tx_data)
        self.blockchain.add_transaction("swap", tx_data, signature)
        self.log(f"Swapping {amount} ENERGY por STAR")

    def add_liquidity(self):
        a = float(self.liq_a_input.text())
        b = float(self.liq_b_input.text())
        lp = self.pool.add_liquidity(self.explorer, a, b)
        tx_data = {"account": self.explorer_id, "pool_id": self.pool.pool_id, "amount_a": a, "amount_b": b}
        signature = self.explorer.sign(tx_data)
        self.blockchain.add_transaction("liquidity", tx_data, signature)
        self.log(f"Adicionado {a} ENERGY e {b} STAR. LP: {lp}")

    def lock_to_solana(self):
        amount = float(self.bridge_amount.text())
        tx_data = {"sender": self.explorer_id, "token_id": "ENERGY", "amount": amount}
        signature = self.explorer.sign(tx_data)
        tx_hash = self.bridge.lock_asset(self.explorer, "ENERGY", amount, signature)
        if tx_hash:
            self.log(f"Locked {amount} ENERGY. Tx: {tx_hash}")

    def start_network_sync(self):
        def sync():
            while True:
                try:
                    msg, _ = self.network.message_queue.get_nowait()
                    if msg["type"] in ["transfer", "swap", "bridge_lock", "liquidity"]:
                        self.blockchain.pending_transactions.append(msg)
                    elif msg["type"] == "block":
                        block = CosmicBlock(**msg["data"])
                        if self.ai.verify_chain(block):
                            self.blockchain.chain.append(block)
                except queue.Empty:
                    time.sleep(0.1)
        threading.Thread(target=sync, daemon=True).start()

    def closeEvent(self, event):
        self.stop_mining()
        self.network.stop()
        self.update_timer.stop()
        self.ai_timer.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = GalacticDEXGUI()
    gui.show()
    sys.exit(app.exec())