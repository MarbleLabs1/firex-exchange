import sys
import os
import datetime
import qtawesome as qta
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
                           QHBoxLayout, QPushButton, QLabel, QLineEdit, QComboBox,
                           QTableWidget, QTableWidgetItem, QProgressBar, QFrame,
                           QSplitter, QMessageBox, QGroupBox, QFormLayout, QSpinBox,
                           QDoubleSpinBox, QCheckBox, QTextEdit, QScrollArea, QSizePolicy,
                           QGridLayout)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize, QRect
from PyQt6.QtGui import QFont, QColor, QPalette, QIcon, QPixmap, QLinearGradient, QBrush, QPainter, QPen
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger
import asyncio
import aiohttp
import json
import hashlib
import hmac
import base64
from typing import Dict, List, Optional, Union
from decimal import Decimal

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import project modules
from config.config import GUI_THEME, GUI_STYLE, DEX_NAME, DEX_VERSION
from blockchain.core import BlockchainInterface
from security.encryption import EncryptionManager
from security.authentication import AuthManager
from utils.error_handler import ErrorHandler
from utils.logger import setup_logger
from utils.rate_limiter import RateLimiter
from utils.monitoring import MonitoringSystem

class DexMainWindow(QMainWindow):
    def __init__(self, dex_app):
        super().__init__()
        self.dex_app = dex_app
        
        # Initialize security and monitoring
        self.encryption_manager = EncryptionManager()
        self.auth_manager = AuthManager()
        self.error_handler = ErrorHandler()
        self.rate_limiter = RateLimiter()
        self.monitoring = MonitoringSystem()
        
        # Setup logging
        setup_logger()
        
        # Initialize UI
        self.setWindowTitle(f"{DEX_NAME} v{DEX_VERSION}")
        self.setMinimumSize(1200, 800)
        
        # Load green stylesheet (Binance-style)
        with open(os.path.join(os.path.dirname(__file__), 'styles_green.qss'), 'r') as f:
            self.setStyleSheet(f.read())
        
        # Initialize UI components
        self.init_ui()
        
        # Set up update timer with rate limiting
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.rate_limited_update)
        self.update_timer.start(1000)  # Update every second
        
        # Initialize security features
        self.init_security()
        
        # Start monitoring
        self.monitoring.start_monitoring()

    def init_security(self):
        """Initialize security features"""
        try:
            # Setup encryption
            self.encryption_manager.initialize()
            
            # Setup authentication
            self.auth_manager.initialize()
            
            # Setup error handling
            self.error_handler.initialize()
            
            # Setup rate limiting
            self.rate_limiter.initialize()
            
            logger.info("Security features initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize security features: {str(e)}")
            self.error_handler.handle_error(e)

    def rate_limited_update(self):
        """Rate-limited data update"""
        if self.rate_limiter.check_rate_limit("ui_update"):
            asyncio.create_task(self.update_data())
        else:
            logger.warning("UI update rate limit exceeded")

    async def update_data(self):
        """Update all UI data with error handling and monitoring"""
        try:
            # Start monitoring this operation
            with self.monitoring.operation("ui_update"):
                # Update order book
                if self.pool_combo.currentText():
                    pool_id = self.pool_combo.currentText()
                    
                    # Fetch data with rate limiting
                    if self.rate_limiter.check_rate_limit("order_book"):
                        order_book = await self.dex_app.dex_trading.get_order_book(pool_id)
                        self.update_order_book(order_book)
                    
                    if self.rate_limiter.check_rate_limit("trades"):
                        trades = await self.dex_app.dex_analytics.get_pool_metrics(pool_id)
                        self.update_trades(trades)
                    
                    if self.rate_limiter.check_rate_limit("analytics"):
                        analytics = await self.dex_app.dex_analytics.get_pool_analytics(pool_id)
                        self.update_analytics(analytics)
                    
                    # Update market making status
                    self.update_market_making_status()
                
        except Exception as e:
            logger.error(f"Error updating UI data: {str(e)}")
            self.error_handler.handle_error(e)
            self.show_error_message("Data Update Error", str(e))

    def show_error_message(self, title: str, message: str):
        """Show error message to user"""
        QMessageBox.critical(self, title, message)

    async def place_order(self):
        """Place a new order with security checks"""
        try:
            # Check authentication
            if not self.auth_manager.is_authenticated():
                self.show_error_message("Authentication Error", "Please log in to place orders")
                return
            
            # Validate inputs
            pool_id = self.pool_combo.currentText()
            side = self.side_combo.currentText().lower()
            
            try:
                amount = Decimal(self.amount_input.text())
                price = Decimal(self.price_input.text())
                slippage = Decimal(self.slippage_input.text()) / 100
            except ValueError:
                self.show_error_message("Input Error", "Invalid numeric values")
                return
            
            # Check rate limit
            if not self.rate_limiter.check_rate_limit("place_order"):
                self.show_error_message("Rate Limit", "Too many orders. Please wait.")
                return
            
            # Start monitoring
            with self.monitoring.operation("place_order"):
                # Encrypt sensitive data
                encrypted_data = self.encryption_manager.encrypt({
                    "amount": str(amount),
                    "price": str(price),
                    "slippage": str(slippage)
                })
                
                # Place order
                order_id = await self.dex_app.dex_trading.create_order(
                    pool_id,
                    side,
                    amount,
                    price,
                    slippage,
                    encrypted_data
                )
                
                if order_id:
                    logger.info(f"Order placed successfully: {order_id}")
                    self.show_success_message("Order Placed", f"Order ID: {order_id}")
                else:
                    logger.error("Failed to place order")
                    self.show_error_message("Order Error", "Failed to place order")
                
        except Exception as e:
            logger.error(f"Error placing order: {str(e)}")
            self.error_handler.handle_error(e)
            self.show_error_message("Order Error", str(e))

    def show_success_message(self, title: str, message: str):
        """Show success message to user"""
        QMessageBox.information(self, title, message)
    
    async def place_order_side(self, side: str):
        """Place order for specific side (buy/sell) with enhanced UI"""
        try:
            # Check authentication
            if not self.auth_manager.is_authenticated():
                self.show_error_message("Authentication Error", "Please log in to place orders")
                return
            
            # Get inputs based on side
            if side == 'buy':
                amount_input = self.buy_amount_input
                price_input = self.buy_price_input
                slippage_input = self.buy_slippage_input
            else:
                amount_input = self.sell_amount_input
                price_input = self.sell_price_input
                slippage_input = self.sell_slippage_input
            
            # Validate inputs
            pool_id = self.pool_combo.currentText()
            if not pool_id:
                self.show_error_message("Input Error", "Please select a pool")
                return
            
            try:
                amount = Decimal(amount_input.text() or "0")
                price = Decimal(price_input.text() or "0")
                slippage = Decimal(slippage_input.text() or "1.0") / 100
                
                if amount <= 0 or price <= 0:
                    raise ValueError("Amount and price must be positive")
                    
            except (ValueError, Exception) as e:
                self.show_error_message("Input Error", "Please enter valid numeric values")
                return
            
            # Check rate limit
            if not self.rate_limiter.check_rate_limit("place_order"):
                self.show_error_message("Rate Limit", "Too many orders. Please wait.")
                return
            
            # Start monitoring
            with self.monitoring.operation("place_order"):
                # Encrypt sensitive data
                encrypted_data = self.encryption_manager.encrypt({
                    "amount": str(amount),
                    "price": str(price),
                    "slippage": str(slippage)
                })
                
                # Place order
                order_id = await self.dex_app.dex_trading.create_order(
                    pool_id,
                    side,
                    amount,
                    price,
                    slippage,
                    encrypted_data
                )
                
                if order_id:
                    logger.info(f"{side.upper()} order placed successfully: {order_id}")
                    self.show_success_message(
                        f"{side.upper()} Order Placed", 
                        f"Order ID: {order_id}\nAmount: {amount}\nPrice: {price}"
                    )
                    
                    # Clear inputs after successful order
                    amount_input.clear()
                    price_input.clear()
                    slippage_input.setText("1.0")
                    
                else:
                    logger.error(f"Failed to place {side} order")
                    self.show_error_message("Order Error", f"Failed to place {side} order")
                    
        except Exception as e:
            logger.error(f"Error placing {side} order: {str(e)}")
            self.error_handler.handle_error(e)
            self.show_error_message("Order Error", str(e))

    async def toggle_strategy(self):
        """Start or stop market making strategy with security checks"""
        try:
            # Check authentication
            if not self.auth_manager.is_authenticated():
                self.show_error_message("Authentication Error", "Please log in to manage strategies")
                return
            
            # Check rate limit
            if not self.rate_limiter.check_rate_limit("toggle_strategy"):
                self.show_error_message("Rate Limit", "Too many strategy changes. Please wait.")
                return
            
            # Start monitoring
            with self.monitoring.operation("toggle_strategy"):
                if self.strategy_btn.text() == "Start Strategy":
                    # Start strategy
                    pool_id = self.pool_combo.currentText()
                    strategy_type = self.strategy_combo.currentText().lower().replace(" ", "_")
                    
                    try:
                        params = {
                            "base_size": Decimal(self.base_size_input.text()),
                            "spread": Decimal(self.spread_input.text()) / 100
                        }
                    except ValueError:
                        self.show_error_message("Input Error", "Invalid numeric values")
                        return
                    
                    # Encrypt strategy parameters
                    encrypted_params = self.encryption_manager.encrypt(params)
                    
                    strategy_id = await self.dex_app.market_maker.start_strategy(
                        pool_id,
                        strategy_type,
                        encrypted_params
                    )
                    
                    if strategy_id:
                        self.strategy_btn.setText("Stop Strategy")
                        logger.info(f"Strategy started: {strategy_id}")
                        self.show_success_message("Strategy Started", f"Strategy ID: {strategy_id}")
                    else:
                        logger.error("Failed to start strategy")
                        self.show_error_message("Strategy Error", "Failed to start strategy")
                        
                else:
                    # Stop strategy
                    for strategy_id in self.dex_app.market_maker.strategies:
                        await self.dex_app.market_maker.stop_strategy(strategy_id)
                    
                    self.strategy_btn.setText("Start Strategy")
                    logger.info("Strategy stopped")
                    self.show_success_message("Strategy Stopped", "All strategies have been stopped")
                    
        except Exception as e:
            logger.error(f"Error toggling strategy: {str(e)}")
            self.error_handler.handle_error(e)
            self.show_error_message("Strategy Error", str(e))

    def closeEvent(self, event):
        """Handle application close"""
        try:
            # Stop monitoring
            self.monitoring.stop_monitoring()
            
            # Clean up resources
            self.encryption_manager.cleanup()
            self.auth_manager.cleanup()
            
            # Save any pending data
            self.save_application_state()
            
            event.accept()
        except Exception as e:
            logger.error(f"Error during application close: {str(e)}")
            self.error_handler.handle_error(e)
            event.accept()

    def save_application_state(self):
        """Save application state"""
        try:
            state = {
                "window_geometry": self.saveGeometry(),
                "window_state": self.saveState(),
                "last_pool": self.pool_combo.currentText(),
                "last_strategy": self.strategy_combo.currentText()
            }
            
            # Encrypt state data
            encrypted_state = self.encryption_manager.encrypt(state)
            
            # Save to file
            with open("app_state.json", "w") as f:
                json.dump(encrypted_state, f)
                
        except Exception as e:
            logger.error(f"Error saving application state: {str(e)}")
            self.error_handler.handle_error(e)

    def init_ui(self):
        """Initialize the user interface"""
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Add professional header
        header_widget = self.create_header_widget()
        main_layout.addWidget(header_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Add trading tab
        trading_tab = self.create_trading_tab()
        self.tab_widget.addTab(trading_tab, "Trading")
        
        # Add analytics tab
        analytics_tab = self.create_analytics_tab()
        self.tab_widget.addTab(analytics_tab, "Analytics")
        
        # Add market making tab
        market_making_tab = self.create_market_making_tab()
        self.tab_widget.addTab(market_making_tab, "Market Making")

    def create_header_widget(self):
        """Create professional header with logo and market tickers"""
        header_widget = QWidget()
        header_widget.setObjectName("header-widget")
        header_widget.setStyleSheet("""
            QWidget#header-widget {
                background-color: #1a1a1a;
                border-bottom: 1px solid #3a3a3a;
                padding: 10px;
            }
        """)
        
        header_layout = QHBoxLayout(header_widget)
        header_layout.setSpacing(20)
        
        # Logo and title
        logo_label = QLabel(f"🔥 {DEX_NAME}")
        logo_label.setObjectName("logo-label")
        logo_label.setStyleSheet("""
            QLabel#logo-label {
                font-size: 20px;
                font-weight: bold;
                color: #4caf50;
                padding: 5px;
            }
        """)
        header_layout.addWidget(logo_label)
        
        # Market tickers
        tickers_layout = QHBoxLayout()
        
        # Sample market tickers (you can populate with real data)
        market_pairs = [
            {"pair": "BTC/USDT", "price": "43,521.30", "change": "+2.45%"},
            {"pair": "ETH/USDT", "price": "2,654.80", "change": "+1.23%"},
            {"pair": "SOL/USDT", "price": "98.45", "change": "-0.87%"}
        ]
        
        for market in market_pairs:
            ticker_widget = self.create_ticker_widget(market)
            tickers_layout.addWidget(ticker_widget)
        
        header_layout.addLayout(tickers_layout)
        
        # Spacer
        header_layout.addStretch()
        
        # Status info
        status_label = QLabel("🟢 Connected")
        status_label.setStyleSheet("""
            QLabel {
                color: #4caf50;
                font-weight: bold;
                padding: 5px;
            }
        """)
        header_layout.addWidget(status_label)
        
        return header_widget
    
    def create_ticker_widget(self, market_data):
        """Create a market ticker widget"""
        ticker_widget = QWidget()
        ticker_widget.setObjectName("market-ticker")
        ticker_widget.setStyleSheet("""
            QWidget#market-ticker {
                background-color: #2a2a2a;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 5px 10px;
                margin: 2px;
            }
        """)
        
        ticker_layout = QVBoxLayout(ticker_widget)
        ticker_layout.setSpacing(2)
        
        # Pair name
        pair_label = QLabel(market_data["pair"])
        pair_label.setObjectName("ticker-pair")
        pair_label.setStyleSheet("""
            QLabel#ticker-pair {
                font-weight: bold;
                color: #ffffff;
                font-size: 12px;
            }
        """)
        ticker_layout.addWidget(pair_label)
        
        # Price
        price_label = QLabel(market_data["price"])
        price_label.setObjectName("ticker-price")
        price_label.setStyleSheet("""
            QLabel#ticker-price {
                font-size: 14px;
                font-weight: bold;
                color: #4caf50;
            }
        """)
        ticker_layout.addWidget(price_label)
        
        # Change
        change_label = QLabel(market_data["change"])
        change_label.setObjectName("ticker-change")
        change_color = "#4caf50" if market_data["change"].startswith("+") else "#f44336"
        change_label.setStyleSheet(f"""
            QLabel#ticker-change {{
                font-size: 11px;
                font-weight: bold;
                color: {change_color};
            }}
        """)
        ticker_layout.addWidget(change_label)
        
        return ticker_widget

    def create_trading_tab(self):
        """Create the trading interface tab"""
        tab = QWidget()
        layout = QHBoxLayout(tab)
        
        # Left panel - Order book and trades
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Order book
        order_book_group = QGroupBox("Order Book")
        order_book_layout = QVBoxLayout(order_book_group)
        
        self.order_book_table = QTableWidget()
        self.order_book_table.setColumnCount(3)
        self.order_book_table.setHorizontalHeaderLabels(["Price", "Amount", "Total"])
        order_book_layout.addWidget(self.order_book_table)
        
        left_layout.addWidget(order_book_group)
        
        # Recent trades
        trades_group = QGroupBox("Recent Trades")
        trades_layout = QVBoxLayout(trades_group)
        
        self.trades_table = QTableWidget()
        self.trades_table.setColumnCount(4)
        self.trades_table.setHorizontalHeaderLabels(["Time", "Price", "Amount", "Side"])
        trades_layout.addWidget(self.trades_table)
        
        left_layout.addWidget(trades_group)
        
        # Right panel - Trading form
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Pool selection
        pool_group = QGroupBox("Select Pool")
        pool_layout = QVBoxLayout(pool_group)
        
        self.pool_combo = QComboBox()
        pool_layout.addWidget(self.pool_combo)
        
        right_layout.addWidget(pool_group)
        
        # Trading form
        trade_group = QGroupBox("Place Order")
        trade_layout = QVBoxLayout(trade_group)
        
        # Create buy/sell tabs
        trade_tabs = QTabWidget()
        trade_tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #3a3a3a; }
            QTabBar::tab { 
                background-color: #2a2a2a; 
                color: #ffffff; 
                padding: 8px 16px; 
                border: 1px solid #3a3a3a; 
                border-bottom: none; 
            }
            QTabBar::tab:selected { 
                background-color: #3a3a3a; 
                border-bottom: 2px solid #4caf50; 
            }
        """)
        
        # Buy tab
        buy_tab = QWidget()
        buy_layout = QGridLayout(buy_tab)
        
        # Amount input
        buy_layout.addWidget(QLabel("Amount:"), 0, 0)
        self.buy_amount_input = QLineEdit()
        buy_layout.addWidget(self.buy_amount_input, 0, 1)
        
        # Price input
        buy_layout.addWidget(QLabel("Price:"), 1, 0)
        self.buy_price_input = QLineEdit()
        buy_layout.addWidget(self.buy_price_input, 1, 1)
        
        # Slippage input
        buy_layout.addWidget(QLabel("Slippage (%):"), 2, 0)
        self.buy_slippage_input = QLineEdit("1.0")
        buy_layout.addWidget(self.buy_slippage_input, 2, 1)
        
        # Buy button
        self.buy_btn = QPushButton("BUY")
        self.buy_btn.setObjectName("buy-button")
        self.buy_btn.setStyleSheet("""
            QPushButton#buy-button {
                background-color: #4caf50;
                color: #ffffff;
                border: none;
                padding: 12px 24px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
                min-height: 40px;
            }
            QPushButton#buy-button:hover {
                background-color: #66bb6a;
            }
            QPushButton#buy-button:pressed {
                background-color: #388e3c;
            }
        """)
        self.buy_btn.clicked.connect(lambda: self.place_order_side('buy'))
        buy_layout.addWidget(self.buy_btn, 3, 0, 1, 2)
        
        trade_tabs.addTab(buy_tab, "Buy")
        
        # Sell tab
        sell_tab = QWidget()
        sell_layout = QGridLayout(sell_tab)
        
        # Amount input
        sell_layout.addWidget(QLabel("Amount:"), 0, 0)
        self.sell_amount_input = QLineEdit()
        sell_layout.addWidget(self.sell_amount_input, 0, 1)
        
        # Price input
        sell_layout.addWidget(QLabel("Price:"), 1, 0)
        self.sell_price_input = QLineEdit()
        sell_layout.addWidget(self.sell_price_input, 1, 1)
        
        # Slippage input
        sell_layout.addWidget(QLabel("Slippage (%):"), 2, 0)
        self.sell_slippage_input = QLineEdit("1.0")
        sell_layout.addWidget(self.sell_slippage_input, 2, 1)
        
        # Sell button
        self.sell_btn = QPushButton("SELL")
        self.sell_btn.setObjectName("sell-button")
        self.sell_btn.setStyleSheet("""
            QPushButton#sell-button {
                background-color: #f44336;
                color: #ffffff;
                border: none;
                padding: 12px 24px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
                min-height: 40px;
            }
            QPushButton#sell-button:hover {
                background-color: #e57373;
            }
            QPushButton#sell-button:pressed {
                background-color: #d32f2f;
            }
        """)
        self.sell_btn.clicked.connect(lambda: self.place_order_side('sell'))
        sell_layout.addWidget(self.sell_btn, 3, 0, 1, 2)
        
        trade_tabs.addTab(sell_tab, "Sell")
        
        trade_layout.addWidget(trade_tabs)
        
        right_layout.addWidget(trade_group)
        
        # Add panels to main layout
        layout.addWidget(left_panel, 2)
        layout.addWidget(right_panel, 1)
        
        return tab

    def create_analytics_tab(self):
        """Create the analytics dashboard tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Market overview
        overview_group = QGroupBox("Market Overview")
        overview_layout = QGridLayout(overview_group)
        
        self.total_volume_label = QLabel("Total Volume (24h):")
        self.total_trades_label = QLabel("Total Trades (24h):")
        self.total_pools_label = QLabel("Total Pools:")
        
        overview_layout.addWidget(self.total_volume_label, 0, 0)
        overview_layout.addWidget(self.total_trades_label, 0, 1)
        overview_layout.addWidget(self.total_pools_label, 0, 2)
        
        layout.addWidget(overview_group)
        
        # Price chart
        chart_group = QGroupBox("Price Chart")
        chart_layout = QVBoxLayout(chart_group)
        
        # Create price chart using plotly
        self.price_chart = go.Figure()
        self.price_chart.update_layout(
            title="Price History",
            xaxis_title="Time",
            yaxis_title="Price",
            template="plotly_dark"
        )
        
        chart_layout.addWidget(self.price_chart)
        
        layout.addWidget(chart_group)
        
        # Pool metrics
        metrics_group = QGroupBox("Pool Metrics")
        metrics_layout = QGridLayout(metrics_group)
        
        self.volatility_label = QLabel("Volatility:")
        self.liquidity_label = QLabel("Liquidity Depth:")
        self.avg_trade_label = QLabel("Avg Trade Size:")
        
        metrics_layout.addWidget(self.volatility_label, 0, 0)
        metrics_layout.addWidget(self.liquidity_label, 0, 1)
        metrics_layout.addWidget(self.avg_trade_label, 0, 2)
        
        layout.addWidget(metrics_group)
        
        return tab

    def create_market_making_tab(self):
        """Create the market making control tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Strategy selection
        strategy_group = QGroupBox("Strategy Configuration")
        strategy_layout = QGridLayout(strategy_group)
        
        # Strategy type
        strategy_layout.addWidget(QLabel("Strategy:"), 0, 0)
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["Constant Spread", "Adaptive Spread", "Mean Reversion"])
        strategy_layout.addWidget(self.strategy_combo, 0, 1)
        
        # Base size
        strategy_layout.addWidget(QLabel("Base Size:"), 1, 0)
        self.base_size_input = QLineEdit("1.0")
        strategy_layout.addWidget(self.base_size_input, 1, 1)
        
        # Spread
        strategy_layout.addWidget(QLabel("Spread (%):"), 2, 0)
        self.spread_input = QLineEdit("1.0")
        strategy_layout.addWidget(self.spread_input, 2, 1)
        
        # Start/Stop button
        self.strategy_btn = QPushButton("Start Strategy")
        self.strategy_btn.clicked.connect(self.toggle_strategy)
        strategy_layout.addWidget(self.strategy_btn, 3, 0, 1, 2)
        
        layout.addWidget(strategy_group)
        
        # Strategy status
        status_group = QGroupBox("Strategy Status")
        status_layout = QVBoxLayout(status_group)
        
        self.status_table = QTableWidget()
        self.status_table.setColumnCount(4)
        self.status_table.setHorizontalHeaderLabels(["Strategy", "Pool", "Status", "Last Update"])
        status_layout.addWidget(self.status_table)
        
        layout.addWidget(status_group)
        
        return tab

    def update_order_book(self, order_book):
        """Update order book display"""
        if not order_book:
            return
            
        self.order_book_table.setRowCount(0)
        
        # Add sell orders (in reverse order)
        for order in reversed(order_book["sell_orders"]):
            row = self.order_book_table.rowCount()
            self.order_book_table.insertRow(row)
            self.order_book_table.setItem(row, 0, QTableWidgetItem(f"{order['price']:.8f}"))
            self.order_book_table.setItem(row, 1, QTableWidgetItem(f"{order['amount']:.8f}"))
            self.order_book_table.setItem(row, 2, QTableWidgetItem(f"{order['price'] * order['amount']:.8f}"))
        
        # Add buy orders
        for order in order_book["buy_orders"]:
            row = self.order_book_table.rowCount()
            self.order_book_table.insertRow(row)
            self.order_book_table.setItem(row, 0, QTableWidgetItem(f"{order['price']:.8f}"))
            self.order_book_table.setItem(row, 1, QTableWidgetItem(f"{order['amount']:.8f}"))
            self.order_book_table.setItem(row, 2, QTableWidgetItem(f"{order['price'] * order['amount']:.8f}"))

    def update_trades(self, trades):
        """Update recent trades display"""
        if not trades:
            return
            
        self.trades_table.setRowCount(0)
        
        for trade in trades.get("recent_trades", []):
            row = self.trades_table.rowCount()
            self.trades_table.insertRow(row)
            self.trades_table.setItem(row, 0, QTableWidgetItem(trade["timestamp"]))
            self.trades_table.setItem(row, 1, QTableWidgetItem(f"{trade['price']:.8f}"))
            self.trades_table.setItem(row, 2, QTableWidgetItem(f"{trade['amount']:.8f}"))
            self.trades_table.setItem(row, 3, QTableWidgetItem(trade["side"]))

    def update_analytics(self, analytics):
        """Update analytics display"""
        if not analytics:
            return
            
        # Update market overview
        self.total_volume_label.setText(f"Total Volume (24h): {analytics['volume_stats']['total']:.2f}")
        self.total_trades_label.setText(f"Total Trades (24h): {analytics['volume_stats']['total']:.0f}")
        
        # Update price chart
        self.price_chart.data = []
        self.price_chart.add_trace(go.Scatter(
            x=[entry["timestamp"] for entry in analytics["price_history"]],
            y=[entry["price"] for entry in analytics["price_history"]],
            mode="lines",
            name="Price"
        ))
        
        # Update pool metrics
        self.volatility_label.setText(f"Volatility: {analytics['price_stats']['volatility']:.4f}")
        self.liquidity_label.setText(f"Liquidity Depth: {analytics['liquidity_stats']['current_depth']:.2f}")
        self.avg_trade_label.setText(f"Avg Trade Size: {analytics['volume_stats']['avg']:.2f}")

    def update_market_making_status(self):
        """Update market making status display"""
        self.status_table.setRowCount(0)
        
        for strategy_id, strategy in self.dex_app.market_maker.strategies.items():
            row = self.status_table.rowCount()
            self.status_table.insertRow(row)
            self.status_table.setItem(row, 0, QTableWidgetItem(strategy["type"]))
            self.status_table.setItem(row, 1, QTableWidgetItem(strategy["pool_id"]))
            self.status_table.setItem(row, 2, QTableWidgetItem(strategy["status"]))
            self.status_table.setItem(row, 3, QTableWidgetItem(str(strategy["last_update"])))

def main(dex_app):
    """Main entry point for the GUI application"""
    try:
        app = QApplication(sys.argv)
        
        # Set dark theme
        app.setStyle("Fusion")
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        app.setPalette(palette)
        
        # Initialize error handling
        error_handler = ErrorHandler()
        error_handler.initialize()
        
        # Create and show main window
        window = DexMainWindow(dex_app)
        window.show()
        
        return app.exec()
        
    except Exception as e:
        logger.error(f"Error in main application: {str(e)}")
        error_handler.handle_error(e)
        return 1

if __name__ == "__main__":
    main()

