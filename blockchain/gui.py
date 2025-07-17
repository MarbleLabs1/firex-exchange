import sys
import json
import asyncio
import threading
from typing import Dict, List, Optional, Any, Callable
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
                            QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit,
                            QListWidget, QMessageBox, QProgressBar, QDialog, QDoubleSpinBox,
                            QFormLayout, QStatusBar, QSplitter)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QEvent
from PyQt6.QtGui import QCloseEvent, QColor

# Import from our merged modules
from client_merged import Client, Message, MessageType
from blockchain_merged import Blockchain, Transaction

class ClientSignals(QObject):
    """Signal class to handle threading between the P2P client and GUI."""
    message_received = pyqtSignal(dict)
    connection_changed = pyqtSignal(bool)
    peer_list_updated = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

class ClientGUI(QMainWindow):
    """Main GUI application for the blockchain P2P client."""
    
    def __init__(self) -> None:
        """Initialize the client GUI application."""
        super().__init__()
        
        # Setup client and blockchain
        self.client: Optional[Client] = None
        self.blockchain = Blockchain()
        self.connected = False
        self.signals = ClientSignals()
        
        # Connect signals
        self.signals.message_received.connect(self.handle_message)
        self.signals.connection_changed.connect(self.handle_connection_change)
        self.signals.peer_list_updated.connect(self.update_peers_list)
        self.signals.error_occurred.connect(self.show_error)
        
        # Setup the UI
        self.init_ui()
        
        # Set up a timer to periodically refresh the balance
        self.balance_timer = QTimer(self)
        self.balance_timer.timeout.connect(self.refresh_balance)
        self.balance_timer.start(10000)  # Refresh every 10 seconds
        
        # Setup client thread
        self.client_thread = None
        self.loop = None

    def init_ui(self) -> None:
        """Initialize the user interface."""
        self.setWindowTitle("Blockchain P2P Client")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget with tabs
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Create main layout
        main_layout = QVBoxLayout(self.central_widget)
        
        # Create top section for connection
        top_section = QWidget()
        top_layout = QHBoxLayout(top_section)
        
        # Nickname input
        self.nickname_label = QLabel("Nickname:")
        self.nickname_input = QLineEdit()
        self.nickname_input.setPlaceholderText("Enter your nickname")
        
        # Connect/Disconnect button
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_to_network)
        
        # Add widgets to top layout
        top_layout.addWidget(self.nickname_label)
        top_layout.addWidget(self.nickname_input)
        top_layout.addWidget(self.connect_button)
        
        # Add top section to main layout
        main_layout.addWidget(top_section)
        
        # Create tab widget
        self.tabs = QTabWidget()
        
        # Create chat tab
        self.chat_tab = QWidget()
        chat_layout = QVBoxLayout(self.chat_tab)
        
        # Chat history
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        
        # Chat input section
        chat_input_section = QWidget()
        chat_input_layout = QHBoxLayout(chat_input_section)
        
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Type your message here")
        self.chat_input.returnPressed.connect(self.send_chat_message)
        
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_chat_message)
        
        chat_input_layout.addWidget(self.chat_input)
        chat_input_layout.addWidget(self.send_button)
        
        # Add widgets to chat layout
        chat_layout.addWidget(self.chat_history)
        chat_layout.addWidget(chat_input_section)
        
        # Create transactions tab
        self.transactions_tab = QWidget()
        transactions_layout = QVBoxLayout(self.transactions_tab)
        
        # Transaction form
        transaction_form = QWidget()
        form_layout = QFormLayout(transaction_form)
        
        self.recipient_input = QLineEdit()
        self.amount_input = QDoubleSpinBox()
        self.amount_input.setRange(0.01, 1000.00)
        self.amount_input.setSingleStep(0.01)
        self.amount_input.setValue(1.00)
        
        self.balance_label = QLabel("Balance: 0.00")
        self.transaction_button = QPushButton("Send Transaction")
        self.transaction_button.clicked.connect(self.send_transaction)
        
        form_layout.addRow("Recipient:", self.recipient_input)
        form_layout.addRow("Amount:", self.amount_input)
        form_layout.addRow("", self.balance_label)
        form_layout.addRow("", self.transaction_button)
        
        # Transaction history
        self.transaction_history = QTextEdit()
        self.transaction_history.setReadOnly(True)
        
        # Add widgets to transactions layout
        transactions_layout.addWidget(transaction_form)
        transactions_layout.addWidget(QLabel("Transaction History:"))
        transactions_layout.addWidget(self.transaction_history)
        
        # Create peers tab
        self.peers_tab = QWidget()
        peers_layout = QVBoxLayout(self.peers_tab)
        
        self.peers_list = QListWidget()
        peers_layout.addWidget(QLabel("Connected Peers:"))
        peers_layout.addWidget(self.peers_list)
        
        # Add tabs to tab widget
        self.tabs.addTab(self.chat_tab, "Chat")
        self.tabs.addTab(self.transactions_tab, "Transactions")
        self.tabs.addTab(self.peers_tab, "Peers")
        
        # Add tab widget to main layout
        main_layout.addWidget(self.tabs)
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Connection status
        self.connection_status = QLabel("Disconnected")
        self.connection_status.setStyleSheet("color: red")
        self.status_bar.addPermanentWidget(self.connection_status)
        
        # Disable chat and transaction widgets initially
        self.chat_input.setEnabled(False)
        self.send_button.setEnabled(False)
        self.recipient_input.setEnabled(False)
        self.amount_input.setEnabled(False)
        self.transaction_button.setEnabled(False)

    def connect_to_network(self) -> None:
        """Connect to the P2P network."""
        if self.connected:
            self.disconnect_from_network()
            return
        
        nickname = self.nickname_input.text().strip()
        if not nickname:
            self.show_error("Please enter a nickname")
            return
        
        # Start the client in a separate thread
        self.client_thread = threading.Thread(target=self.run_client, args=(nickname,))
        self.client_thread.daemon = True
        self.client_thread.start()
        
        # Update UI
        self.connect_button.setText("Disconnect")
        self.nickname_input.setEnabled(False)
        self.chat_input.setEnabled(True)
        self.send_button.setEnabled(True)
        self.recipient_input.setEnabled(True)
        self.amount_input.setEnabled(True)
        self.transaction_button.setEnabled(True)
        
        self.update_connection_status(True)
        
    def run_client(self, nickname: str) -> None:
        """Run the P2P client in a separate thread."""
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            # Create and start the client
            self.client = Client(nickname)
            
            # Set up callbacks
            self.client.set_message_callback(self.on_message_received)
            self.client.set_peer_list_callback(self.on_peer_list_updated)
            self.client.set_connection_callback(self.on_connection_changed)
            self.client.set_error_callback(self.on_error_occurred)
            
            # Run the client
            self.loop.run_until_complete(self.client.start())
            self.loop.run_forever()
        except Exception as e:
            self.on_error_occurred(str(e))
        finally:
            if self.loop:
                self.loop.close()
            
    def on_message_received(self, message: Dict[str, Any]) -> None:
        """Callback for when a message is received from the network."""
        self.signals.message_received.emit(message)
    
    def on_peer_list_updated(self, peers: List[str]) -> None:
        """Callback for when the peer list is updated."""
        self.signals.peer_list_updated.emit(peers)
    
    def on_connection_changed(self, connected: bool) -> None:
        """Callback for when the connection status changes."""
        self.connected = connected
        self.signals.connection_changed.emit(connected)
    
    def on_error_occurred(self, error_message: str) -> None:
        """Callback for when an error occurs."""
        self.signals.error_occurred.emit(error_message)
    
    def disconnect_from_network(self) -> None:
        """Disconnect from the P2P network."""
        if not self.connected or not self.client:
            return
        
        # Stop the client
        if self.loop:
            asyncio.run_coroutine_threadsafe(self.client.stop(), self.loop)
        
        # Update UI
        self.connect_button.setText("Connect")
        self.nickname_input.setEnabled(True)
        self.chat_input.setEnabled(False)
        self.send_button.setEnabled(False)
        self.recipient_input.setEnabled(False)
        self.amount_input.setEnabled(False)
        self.transaction_button.setEnabled(False)
        
        self.update_connection_status(False)
        
        # Wait for the client thread to finish
        if self.client_thread and self.client_thread.is_alive():
            self.client_thread.join(timeout=1.0)
            self.client_thread = None

    def send_chat_message(self) -> None:
        """Send a chat message to the P2P network."""
        if not self.connected or not self.client:
            self.show_error("Not connected to the network")
            return
            
        message = self.chat_input.text().strip()
        if not message:
            return
            
        # Create a chat message
        chat_data = {
            "text": message,
            "sender": self.nickname_input.text()
        }
            
        # Send the message
        if self.loop:
            asyncio.run_coroutine_threadsafe(
                self.client.send_message(MessageType.CHAT, chat_data),
                self.loop
            )
            
        # Clear the input field
        self.chat_input.clear()
            
        # Add message to chat history (for immediate feedback)
        self.chat_history.append(f"<b>You:</b> {message}")
        self.chat_history.ensureCursorVisible()

    def send_transaction(self) -> None:
        """Send a transaction to the blockchain network."""
        if not self.connected or not self.client:
            self.show_error("Not connected to the network")
            return
            
        recipient = self.recipient_input.text().strip()
        amount = self.amount_input.value()
            
        if not recipient:
            self.show_error("Please enter a recipient address")
            return
            
        if amount <= 0:
            self.show_error("Please enter a valid amount")
            return
            
        # Create a transaction
        sender = self.nickname_input.text()  # Using nickname as address for simplicity
        try:
            transaction = Transaction(sender, recipient, amount)
            
            # Add to blockchain and propagate to network
            self.blockchain.add_transaction(transaction)
            
            # Send transaction data to peers
            tx_data = {
                "sender": sender,
                "recipient": recipient,
                "amount": amount,
                "timestamp": transaction.timestamp
            }
            
            if self.loop:
                asyncio.run_coroutine_threadsafe(
                    self.client.send_message(MessageType.TRANSACTION, tx_data),
                    self.loop
                )
            
            # Show success message
            self.transaction_history.append(
                f"<b>Transaction sent:</b> {amount} coins to {recipient}"
            )
            self.transaction_history.ensureCursorVisible()
            
            # Clear recipient field
            self.recipient_input.clear()
            
            # Refresh balance
            self.refresh_balance()
            
        except Exception as e:
            self.show_error(f"Transaction error: {str(e)}")

    def update_connection_status(self, connected: bool) -> None:
        """Update the connection status in the UI."""
        self.connected = connected
        
        if connected:
            self.connection_status.setText("Connected")
            self.connection_status.setStyleSheet("color: green")
            self.status_bar.showMessage("Connected to P2P network", 5000)
        else:
            self.connection_status.setText("Disconnected")
            self.connection_status.setStyleSheet("color: red")
            self.status_bar.showMessage("Disconnected from P2P network", 5000)

    def handle_message(self, message: Dict[str, Any]) -> None:
        """Handle incoming messages from the P2P network."""
        try:
            message_type = message.get("type")
            data = message.get("data", {})
            sender = data.get("sender", "Unknown")
            
            if message_type == MessageType.CHAT.value:
                # Handle chat message
                text = data.get("text", "")
                if text and sender != self.nickname_input

#!/usr/bin/env python3
"""
P2P Client GUI Application with PyQt6

This module provides a graphical user interface for the P2P client.
It includes tabs for chat, transactions, and nickname settings,
while handling asynchronous P2P operations in a non-blocking way.
"""

import sys
import asyncio
import threading
import json
import logging
import time
from typing import Dict, List, Optional, Any, Callable

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QTabWidget,
    QGroupBox, QFormLayout, QDoubleSpinBox, QComboBox, QCheckBox,
    QMessageBox, QStatusBar, QSpinBox, QSplitter
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QIcon, QColor, QTextCursor, QFont

# Import the Client class from client_merged.py
from client_merged import Client, MessageType, PeerConnection, ConnectionState


class SignalHandler(QObject):
    """Bridge between async events and Qt signals."""
    message_received = pyqtSignal(dict)
    connection_changed = pyqtSignal(str, bool)
    peers_updated = pyqtSignal(list)
    error_occurred = pyqtSignal(str)


class AsyncHelper:
    """Helper class to run async tasks from synchronous code."""
    def __init__(self, loop):
        self.loop = loop
        
    def run_coroutine(self, coro, callback=None):
        """Run a coroutine in the asyncio event loop."""
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        if callback:
            future.add_done_callback(lambda f: callback(f.result()))
        return future
        
    def call_soon(self, callback, *args):
        """Schedule a callback to be called in the asyncio event loop."""
        self.loop.call_soon_threadsafe(callback, *args)


class ClientGUI(QMainWindow):
    """Main GUI window for the P2P client application."""
    
    def __init__(self):
        super().__init__()
        
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("ClientGUI")
        
        # Initialize the signal handler
        self.signal_handler = SignalHandler()
        
        # Initial UI setup
        self.setWindowTitle("P2P Client")
        self.setGeometry(100, 100, 800, 600)
        
        # Initialize member variables
        self.client = None
        self.loop = None
        self.async_helper = None
        self.connection_timer = QTimer(self)
        self.connection_timer.timeout.connect(self.update_connection_status)
        self.connection_timer.start(5000)  # 5 seconds
        
        # Setup UI components
        self.init_ui()
        
        # Connect signals to slots
        self.connect_signals()
        
        # Start asyncio loop in a separate thread
        self.start_asyncio_loop()
        
        # Initialize the client (without connecting yet)
        self.init_client()
        
        self.logger.info("GUI initialized")
        
    def init_ui(self):
        """Initialize the user interface components."""
        # Central widget and main layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Connection status indicators
        self.connection_status = QLabel("Disconnected")
        self.connection_status.setStyleSheet("color: red;")
        self.status_bar.addPermanentWidget(self.connection_status)
        
        self.peers_count = QLabel("Peers: 0")
        self.status_bar.addPermanentWidget(self.peers_count)
        
        # Create tabs
        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)
        
        # Add the three main tabs
        self.setup_connection_tab()
        self.setup_chat_tab()
        self.setup_transaction_tab()
        
    def setup_connection_tab(self):
        """Create the connection tab for nickname and connection settings."""
        connection_tab = QWidget()
        layout = QVBoxLayout(connection_tab)
        
        # Nickname group
        nickname_group = QGroupBox("Nickname")
        nickname_layout = QFormLayout()
        
        self.nickname_input = QLineEdit("User")
        nickname_layout.addRow("Set Nickname:", self.nickname_input)
        
        self.apply_nickname_button = QPushButton("Apply")
        self.apply_nickname_button.clicked.connect(self.apply_nickname)
        nickname_layout.addRow("", self.apply_nickname_button)
        
        nickname_group.setLayout(nickname_layout)
        layout.addWidget(nickname_group)
        
        # Connection group
        connection_group = QGroupBox("Connection")
        connection_layout = QFormLayout()
        
        self.bootstrap_peers_input = QTextEdit()
        self.bootstrap_peers_input.setPlaceholderText(
            "Enter bootstrap peers (one per line)\n"
            "Example: /ip4/127.0.0.1/tcp/4001/p2p/QmPeerID"
        )
        self.bootstrap_peers_input.setMaximumHeight(100)
        connection_layout.addRow("Bootstrap Peers:", self.bootstrap_peers_input)
        
        self.port_input = QSpinBox()
        self.port_input.setRange(1024, 65535)
        self.port_input.setValue(4001)
        connection_layout.addRow("Listen Port:", self.port_input)
        
        button_layout = QHBoxLayout()
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_to_network)
        
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.clicked.connect(self.disconnect_from_network)
        self.disconnect_button.setEnabled(False)
        
        button_layout.addWidget(self.connect_button)
        button_layout.addWidget(self.disconnect_button)
        connection_layout.addRow("", button_layout)
        
        connection_group.setLayout(connection_layout)
        layout.addWidget(connection_group)
        
        # Peers group
        peers_group = QGroupBox("Connected Peers")
        peers_layout = QVBoxLayout()
        
        self.peers_list = QTextEdit()
        self.peers_list.setReadOnly(True)
        peers_layout.addWidget(self.peers_list)
        
        peers_group.setLayout(peers_layout)
        layout.addWidget(peers_group)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
        self.tabs.addTab(connection_tab, "Connection")
        
    def setup_chat_tab(self):
        """Create the chat tab for messaging functionality."""
        chat_tab = QWidget()
        layout = QVBoxLayout(chat_tab)
        
        # Chat display area
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        layout.addWidget(self.chat_display)
        
        # Message input and send button
        input_layout = QHBoxLayout()
        
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type a message...")
        self.message_input.returnPressed.connect(self.send_chat_message)
        input_layout.addWidget(self.message_input)
        
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_chat_message)
        input_layout.addWidget(self.send_button)
        
        layout.addLayout(input_layout)
        
        self.tabs.addTab(chat_tab, "Chat")
        
    def setup_transaction_tab(self):
        """Create the transaction tab for blockchain operations."""
        transaction_tab = QWidget()
        layout = QVBoxLayout(transaction_tab)
        
        # Transaction form
        transaction_group = QGroupBox("Create Transaction")
        transaction_layout = QFormLayout()
        
        self.recipient_input = QLineEdit()
        transaction_layout.addRow("Recipient:", self.recipient_input)
        
        self.amount_input = QDoubleSpinBox()
        self.amount_input.setRange(0.01, 1000000.00)
        self.amount_input.setValue(1.00)
        self.amount_input.setSingleStep(0.01)
        transaction_layout.addRow("Amount:", self.amount_input)
        
        self.send_transaction_button = QPushButton("Send Transaction")
        self.send_transaction_button.clicked.connect(self.send_transaction)
        transaction_layout.addRow("", self.send_transaction_button)
        
        transaction_group.setLayout(transaction_layout)
        layout.addWidget(transaction_group)
        
        # Transaction history
        history_group = QGroupBox("Transaction History")
        history_layout = QVBoxLayout()
        
        self.transaction_history = QTextEdit()
        self.transaction_history.setReadOnly(True)
        history_layout.addWidget(self.transaction_history)
        
        history_group.setLayout(history_layout)
        layout.addWidget(history_group)
        
        # Balance display
        balance_group = QGroupBox("Balance")
        balance_layout = QHBoxLayout()
        
        self.balance_label = QLabel("0.00")
        self.balance_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        balance_layout.addWidget(self.balance_label)
        
        self.refresh_balance_button = QPushButton("Refresh")
        self.refresh_balance_button.clicked.connect(self.refresh_balance)
        balance_layout.addWidget(self.refresh_balance_button)
        
        balance_group.setLayout(balance_layout)
        layout.addWidget(balance_group)
        
        self.tabs.addTab(transaction_tab, "Transactions")
        
    def connect_signals(self):
        """Connect signal handlers to their slots."""
        # Connect custom signals
        self.signal_handler.message_received.connect(self.handle_message)
        self.signal_handler.connection_changed.connect(self.handle_connection_change)
        self.signal_handler.peers_updated.connect(self.update_peers_list)
        self.signal_handler.error_occurred.connect(self.show_error)
        
    def start_asyncio_loop(self):
        """Start the asyncio event loop in a separate thread."""
        self.loop = asyncio.new_event_loop()
        self.async_helper = AsyncHelper(self.loop)
        
        def run_loop():
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()
            
        self.loop_thread = threading.Thread(target=run_loop, daemon=True)
        self.loop_thread.start()
        self.logger.info("Asyncio loop started in separate thread")
        
    def init_client(self):
        """Initialize the P2P client without connecting."""
        self.client = Client(
            nickname=self.nickname_input.text(),
            port=self.port_input.value()
        )
        
        # Setup message and event callbacks
        self.client.set_message_callback(self._message_callback)
        self.client.set_connection_callback(self._connection_callback)
        self.client.set_error_callback(self._error_callback)
        self.logger.info("Client initialized")
        
    def _message_callback(self, message: dict):
        """Callback for receiving messages from the client."""
        self.signal_handler.message_received.emit(message)
        
    def _connection_callback(self, peer_id: str, connected: bool):
        """Callback for connection state changes."""
        self.signal_handler.connection_changed.emit(peer_id, connected)
        
    def _error_callback(self, error_message: str):
        """Callback for errors from the client."""
        self.signal_handler.error_occurred.emit(error_message)
        
    def apply_nickname(self):
        """Apply the nickname from the input field."""
        nickname = self.nickname_input.text().strip()
        if not nickname:
            self.show_error("Nickname cannot be empty")
            return
            
        if self.client:
            self.client.set_nickname(nickname)
            self.status_bar.showMessage(f"Nickname set to: {nickname}", 3000)
            self.logger.info(f"Nickname set to: {nickname}")
            
    def connect_to_network(self):
        """Connect to the P2P network."""
        if not self.client:
            self.init_client()
            
        # Get bootstrap peers from input
        bootstrap_peers = []
        peer_text = self.bootstrap_peers_input.toPlainText().strip()
        if peer_text:
            bootstrap_peers = [p.strip() for p in peer_text.split('\n') if p.strip()]
            
        # Start the client
        async def connect():
            try:
                await self.client.start(bootstrap_peers)
                return True
            except Exception as e:
                self.logger.error(f"Failed to connect: {str(e)}")
                return False
                
        def on_connected(success):
            if success:
                self.connect_button.setEnabled(False)
                self.disconnect_button.setEnabled(True)
                self.connection_status.setText("Connected")
                self.connection_status.setStyleSheet("color: green;")
                self.status_bar.showMessage("Connected to P2P network", 3000)
                
                # Update UI with available peers
                self.async_helper.run_coroutine(
                    self.client.get_peers(),
                    lambda peers: self.signal_handler.peers_updated.emit(peers)
                )
            else:
                self.show_error("Failed to connect to the network")
                
        self.async_helper.run_coroutine(connect(), on_connected)
        
    def disconnect_from_network(self):
        """Disconnect from the P2P network."""
        if self.client:
            async def disconnect():
                try:
                    await self.client.stop()
                    return True
                except Exception as e:
                    self.logger.error(f"Error during disconnect: {str(e)}")
                    return False
                    
            def on_disconnected(success):
                if success:
                    self.connect_button.setEnabled(True)
                    self.disconnect_button.setEnabled(False)
                    self.connection_status.setText("Disconnected")
                    self.connection_status.setStyleSheet("color: red;")
                    self.peers_list.clear()
                    self.peers_count.setText("Peers: 0")
                    self.status_bar.showMessage("Disconnected from P2P network", 3000)
                
            self.async_helper.run_coroutine(disconnect(), on_disconnected)
        
    def send_chat_message(self):
        """Send a chat message to connected peers."""
        if not self.client:
            self.show_error("Not connected to the network")
            return
            
        message = self.message_input.text().strip()
        if not message:
            return
            
        nickname = self.nickname_input.text()
        message_data = {
            "text": message,
            "sender": nickname,
            "timestamp": time.time()
        }
        
        # Display own message immediately
        self.chat_display.append(f"<b>You:</b> {message}")
        self.message_input.clear()
        
        # Send message via client
        async def send_msg():
            try:
                await self.client.send_message(MessageType.CHAT, message_data)
                return True
            except Exception as e:
                self.logger.error(f"Failed to send message: {str(e)}")
                return False
                
        def on_sent(success):
            if not success:
                self.show_error("Failed to send message")
                
        self.async_helper.run_coroutine(send_msg(), on_sent)
        
    def send_transaction(self):
        """Send a transaction to the network."""
        if not self.client:
            self.show_error("Not connected to the network")
            return
            
        recipient = self.recipient_input.text().strip()
        if not recipient:
            self.show_error("Please enter a recipient")
            return
            
        amount = self.amount_input.value()
        if amount <= 0:
            self.show_error("Amount must be greater than zero")
            return
            
        sender = self.nickname_input.text()
        transaction_data = {
            "sender": sender,
            "recipient": recipient,
            "amount": amount,
            "timestamp": time.time()
        }
        
        # Display the transaction in the history
        self.transaction_history.append(
            f"<b>Transaction:</b> {amount} coins to {recipient}"
        )
        self.recipient_input.clear()
        
        # Send transaction via client
        async def send_tx():
            try:
                await self.client.send_message(MessageType.TRANSACTION, transaction_data)
                return True
            except Exception as e:
                self.logger.error(f"Failed to send transaction: {str(e)}")
                return False
                
        def on_sent(success):
            if success:
                self.status_bar.showMessage("Transaction sent successfully", 3000)
                self.refresh_balance()
            else:
                self.show_error("Failed to send transaction")
                
        self.async_helper.run_coroutine(send_tx(), on_sent)
        
    def handle_message(self, message):
        """Handle incoming messages from the P2P network."""
        try:
            message_type = message.get("type")
            data = message.get("data", {})
            
            if message_type == MessageType.CHAT.value:
                # Handle chat message
                text = data.get("text", "")
                sender = data.get("sender", "Unknown")
                
                # Don't display our own messages again
                if sender != self.nickname_input.text():
                    self.chat_display.append(f"<b>{sender}:</b> {text}")
                    
            elif message_type == MessageType.TRANSACTION.value:
                # Handle transaction message
                sender = data.get("sender", "Unknown")
                recipient = data.get("recipient", "Unknown")
                amount = data.get("amount", 0)
                
                # Only show transactions we're involved in
                nickname = self.nickname_input.text()
                if sender == nickname or recipient == nickname:
                    self.transaction_history.append(
                        f"<b>Transaction:</b> {sender} sent {amount} coins to {recipient}"
                    )
                    self.refresh_balance()
                    
            elif message_type == MessageType.BLOCKCHAIN.value:
                # Handle blockchain updates
                self.logger.info("Received blockchain update")
                self.refresh_balance()
                
        except Exception as e:
            self.logger.error(f"Error handling message: {str(e)}")
            
    def update_peers_list(self, peers):
        """Update the displayed list of connected peers."""
        try:
            self.peers_list.clear()
            self.peers_count.setText(f"Peers: {len(peers)}")
            
            if not peers:
                self.peers_list.setText("No peers connected")
                return
                
            peer_text = ""
            for i, peer in enumerate(peers, 1):
                peer_text += f"{i}. {peer}\n"
                
            self.peers_list.setText(peer_text)
            
        except Exception as e:
            self.logger.error(f"Error updating peers list: {str(e)}")
            
    def show_error(self, message):
        """Display an error message dialog to the user."""
        self.logger.error(message)
        QMessageBox.critical(self, "Error", message)
        
    def refresh_balance(self):
        """Refresh the displayed balance from the blockchain."""
        if not self.client:
            return
            
        try:
            # For a real implementation, this would query the blockchain
            # For now, we'll just simulate a balance calculation
            nickname = self.nickname_input.text()
            
            async def get_balance():
                # This would be an actual blockchain query in a real implementation
                # Simulating a balance calculation for demonstration
                await asyncio.sleep(0.1)  # Simulate blockchain query delay
                
                # Simple simulated balance 
                balance = 100.0  # Default balance
                
                # In a real implementation, you would call:
                # balance = blockchain.get_balance(nickname)
                return balance
                
            def update_balance_display(balance):
                self.balance_label.setText(f"{balance:.2f}")
                
            self.async_helper.run_coroutine(get_balance(), update_balance_display)
            
        except Exception as e:
            self.logger.error(f"Failed to refresh balance: {str(e)}")
            
    def update_connection_status(self):
        """Update the connection status in the UI."""
        if not self.client:
            return
            
        async def check_connected():
            try:
                is_connected = self.client.is_connected()
                peers = await self.client.get_peers()
                return is_connected, peers
            except Exception as e:
                self.logger.error(f"Error checking connection: {str(e)}")
                return False, []
                
        def update_status(result):
            is_connected, peers = result
            
            if is_connected:
                self.connection_status.setText("Connected")
                self.connection_status.setStyleSheet("color: green;")
                self.peers_count.setText(f"Peers: {len(peers)}")
                self.signal_handler.peers_updated.emit(peers)
            else:
                self.connection_status.setText("Disconnected")
                self.connection_status.setStyleSheet("color: red;")
                self.peers_count.setText("Peers: 0")
                
        self.async_helper.run_coroutine(check_connected(), update_status)
        
    def handle_connection_change(self, peer_id, connected):
        """Handle connection status changes for specific peers."""
        if connected:
            self.status_bar.showMessage(f"New peer connected: {peer_id}", 3000)
        else:
            self.status_bar.showMessage(f"Peer disconnected: {peer_id}", 3000)
            
        # Update the peers list
        if self.client:
            self.async_helper.run_coroutine(
                self.client.get_peers(),
                lambda peers: self.signal_handler.peers_updated.emit(peers)
            )
            
    def closeEvent(self, event):
        """Handle application closure and cleanup."""
        if self.client and self.client.is_connected():
            # Show confirmation dialog
            reply = QMessageBox.question(
                self, "Confirm Exit",
                "You are still connected to the P2P network. Disconnect and quit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Disconnect and then close
                async def disconnect_and_close():
                    try:
                        await self.client.stop()
                        return True
                    except Exception as e:
                        self.logger.error(f"Error during disconnect: {str(e)}")
                        return False
                        
                # We can't use the async_helper here because we need to block
                # until disconnection is complete
                future = asyncio.run_coroutine_threadsafe(
                    disconnect_and_close(), self.loop
                )
                
                try:
                    # Wait for up to 2 seconds for disconnection
                    future.result(timeout=2.0)
                except Exception as e:
                    self.logger.error(f"Error during shutdown: {str(e)}")
                    
                # Stop the asyncio loop
                if self.loop and self.loop.is_running():
                    self.loop.call_soon_threadsafe(self.loop.stop)
                    
                # Accept the close event
                event.accept()
            else:
                # Reject the close event
                event.ignore()
        else:
            # Not connected, just close
            if self.loop and self.loop.is_running():
                self.loop.call_soon_threadsafe(self.loop.stop)
                
            event.accept()


if __name__ == "__main__":
    # Set up application
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Use Fusion style for consistent look across platforms
    
    # Create and show the main window
    window = ClientGUI()
    window.show()
    
    # Start the application event loop
    sys.exit(app.exec())

