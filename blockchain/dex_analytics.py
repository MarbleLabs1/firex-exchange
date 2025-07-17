import os
import json
import time
import asyncio
import random
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger

class DexAnalytics:
    """Analytics for DEX trading data"""
    
    def __init__(self, dex_trading):
        self.dex_trading = dex_trading
        self.price_history = {}
        self.volume_history = {}
        self.liquidity_history = {}
        self.max_history_points = 1000
        self.running = False
        self.task = None
    
    async def start(self) -> bool:
        """Start the analytics service"""
        try:
            if self.running:
                return True
            
            self.running = True
            self.task = asyncio.create_task(self._analytics_loop())
            
            logger.info("DEX analytics service started")
            return True
        except Exception as e:
            logger.error(f"Error starting DEX analytics service: {str(e)}")
            return False
    
    async def stop(self) -> bool:
        """Stop the analytics service"""
        try:
            if not self.running:
                return True
            
            self.running = False
            if self.task:
                self.task.cancel()
                try:
                    await self.task
                except asyncio.CancelledError:
                    pass
                self.task = None
            
            logger.info("DEX analytics service stopped")
            return True
        except Exception as e:
            logger.error(f"Error stopping DEX analytics service: {str(e)}")
            return False
    
    async def _analytics_loop(self):
        """Background task to collect and process analytics data"""
        while self.running:
            try:
                # Update analytics for all pools
                for pool_id in self.dex_trading.pools.keys():
                    await self._update_pool_analytics(pool_id)
                
                # Sleep to avoid excessive processing
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in analytics loop: {str(e)}")
                await asyncio.sleep(5)
    
    async def _update_pool_analytics(self, pool_id: str):
        """Update analytics data for a specific pool"""
        try:
            # Initialize history for this pool if not exists
            if pool_id not in self.price_history:
                self.price_history[pool_id] = []
                self.volume_history[pool_id] = []
                self.liquidity_history[pool_id] = []
            
            # Get current pool data
            current_price = self.dex_trading.pools[pool_id]["current_price"]
            
            # Get recent trades for volume calculation
            recent_trades = await self.dex_trading.get_trades(pool_id, limit=100)
            recent_volume = sum(trade["amount"] * trade["price"] for trade in recent_trades)
            
            # Calculate liquidity (in a real app this would come from the blockchain)
            liquidity = self._estimate_pool_liquidity(pool_id)
            
            # Add data point with timestamp
            timestamp = time.time()
            self.price_history[pool_id].append((timestamp, current_price))
            self.volume_history[pool_id].append((timestamp, recent_volume))
            self.liquidity_history[pool_id].append((timestamp, liquidity))
            
            # Trim history to max points
            if len(self.price_history[pool_id]) > self.max_history_points:
                self.price_history[pool_id] = self.price_history[pool_id][-self.max_history_points:]
            if len(self.volume_history[pool_id]) > self.max_history_points:
                self.volume_history[pool_id] = self.volume_history[pool_id][-self.max_history_points:]
            if len(self.liquidity_history[pool_id]) > self.max_history_points:
                self.liquidity_history[pool_id] = self.liquidity_history[pool_id][-self.max_history_points:]
        except Exception as e:
            logger.error(f"Error updating pool analytics for {pool_id}: {str(e)}")
    
    def _estimate_pool_liquidity(self, pool_id: str) -> float:
        """Estimate liquidity for a pool (in a real app, this would come from blockchain)"""
        try:
            # For demo purposes, generate a simulated liquidity value
            base_liquidity = 1000000  # $1M base liquidity
            random_factor = random.uniform(0.95, 1.05)  # +/- 5% randomness
            
            if pool_id == "SOL/USDC":
                return base_liquidity * 2.5 * random_factor  # $2.5M
            elif pool_id == "ETH/USDC":
                return base_liquidity * 5 * random_factor  # $5M
            elif pool_id == "BTC/USDC":
                return base_liquidity * 10 * random_factor  # $10M
            else:
                return base_liquidity * random_factor  # $1M
        except Exception as e:
            logger.error(f"Error estimating pool liquidity: {str(e)}")
            return 0.0
    
    async def get_pool_analytics(self, pool_id: str) -> Dict[str, Any]:
        """Get analytics for a specific pool"""
        try:
            if pool_id not in self.dex_trading.pools:
                logger.error(f"Pool {pool_id} not found")
                return {}
            
            # Calculate price statistics
            price_stats = self._calculate_price_stats(pool_id)
            
            # Calculate volume statistics
            volume_stats = self._calculate_volume_stats(pool_id)
            
            # Calculate liquidity statistics
            liquidity_stats = self._calculate_liquidity_stats(pool_id)
            
            # Get price history for charts (last 24 hours)
            price_history = self._get_recent_price_history(pool_id, hours=24)
            
            return {
                "pool_id": pool_id,
                "price_stats": price_stats,
                "volume_stats": volume_stats,
                "liquidity_stats": liquidity_stats,
                "price_history": price_history
            }
        except Exception as e:
            logger.error(f"Error getting pool analytics: {str(e)}")
            return {}
    
    def _calculate_price_stats(self, pool_id: str) -> Dict[str, float]:
        """Calculate price statistics for a pool"""
        try:
            if pool_id not in self.price_history or not self.price_history[pool_id]:
                return {
                    "current": self.dex_trading.pools[pool_id]["current_price"],
                    "change_24h": 0.0,
                    "change_24h_percent": 0.0,
                    "high_24h": self.dex_trading.pools[pool_id]["current_price"],
                    "low_24h": self.dex_trading.pools[pool_id]["current_price"],
                    "volatility": 0.0
                }
            
            # Get current price and price history
            current_price = self.dex_trading.pools[pool_id]["current_price"]
            
            # Get price points for the last 24 hours
            cutoff_time = time.time() - (24 * 60 * 60)  # 24 hours ago
            prices_24h = [p[1] for p in self.price_history[pool_id] if p[0] >= cutoff_time]
            
            if not prices_24h:
                prices_24h = [current_price]
            
            # Calculate statistics
            price_24h_ago = self.price_history[pool_id][0][1] if len(self.price_history[pool_id]) > 0 else current_price
            change_24h = current_price - price_24h_ago
            change_24h_percent = (change_24h / price_24h_ago) * 100 if price_24h_ago > 0 else 0.0
            high_24h = max(prices_24h)
            low_24h = min(prices_24h)
            
            # Calculate volatility (standard deviation of returns)
            if len(prices_24h) > 1:
                prices_array = np.array(prices_24h)
                returns = np.diff(prices_array) / prices_array[:-1]
                volatility = float(np.std(returns) * 100)  # Percentage
            else:
                volatility = 0.0
            
            return {
                "current": current_price,
                "change_24h": change_24h,
                "change_24h_percent": change_24h_percent,
                "high_24h": high_24h,
                "low_24h": low_24h,
                "volatility": volatility
            }
        except Exception as e:
            logger.error(f"Error calculating price stats: {str(e)}")
            return {
                "current": self.dex_trading.pools[pool_id]["current_price"],
                "change_24h": 0.0,
                "change_24h_percent": 0.0,
                "high_24h": self.dex_trading.pools[pool_id]["current_price"],
                "low_24h": self.dex_trading.pools[pool_id]["current_price"],
                "volatility": 0.0
            }
    
    def _calculate_volume_stats(self, pool_id: str) -> Dict[str, float]:
        """Calculate volume statistics for a pool"""
        try:
            if pool_id not in self.volume_history or not self.volume_history[pool_id]:
                return {
                    "total": 0.0,
                    "avg": 0.0,
                    "max": 0.0
                }
            
            # Get volume points for the last 24 hours
            cutoff_time = time.time() - (24 * 60 * 60)  # 24 hours ago
            volumes_24h = [v[1] for v in self.volume_history[pool_id] if v[0] >= cutoff_time]
            
            if not volumes_24h:
                return {
                    "total": 0.0,
                    "avg": 0.0,
                    "max": 0.0
                }
            
            # Calculate statistics
            total_volume = sum(volumes_24h)
            avg_volume = total_volume / len(volumes_24h) if volumes_24h else 0.0
            max_volume = max(volumes_24h) if volumes_24h else 0.0
            
            return {
                "total": total_volume,
                "avg": avg_volume,
                "max": max_volume
            }
        except Exception as e:
            logger.error(f"Error calculating volume stats: {str(e)}")
            return {
                "total": 0.0,
                "avg": 0.0,
                "max": 0.0
            }
    
    def _calculate_liquidity_stats(self, pool_id: str) -> Dict[str, float]:
        """Calculate liquidity statistics for a pool"""
        try:
            if pool_id not in self.liquidity_history or not self.liquidity_history[pool_id]:
                return {
                    "current_depth": 0.0,
                    "change_24h": 0.0,
                    "change_24h_percent": 0.0
                }
            
            # Get current liquidity and liquidity history
            current_liquidity = self.liquidity_history[pool_id][-1][1] if self.liquidity_history[pool_id] else 0.0
            
            # Get liquidity points for the last 24 hours
            cutoff_time = time.time() - (24 * 60 * 60)  # 24 hours ago
            liquidity_24h_ago = next((l[1] for l in self.liquidity_history[pool_id] if l[0] >= cutoff_time), current_liquidity)
            
            # Calculate statistics
            change_24h = current_liquidity - liquidity_24h_ago
            change_24h_percent = (change_24h / liquidity_24h_ago) * 100 if liquidity_24h_ago > 0 else 0.0
            
            return {
                "current_depth": current_liquidity,
                "change_24h": change_24h,
                "change_24h_percent": change_24h_percent
            }
        except Exception as e:
            logger.error(f"Error calculating liquidity stats: {str(e)}")
            return {
                "current_depth": 0.0,
                "change_24h": 0.0,
                "change_24h_percent": 0.0
            }
    
    def _get_recent_price_history(self, pool_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent price history for charts"""
        try:
            if pool_id not in self.price_history or not self.price_history[pool_id]:
                # Generate sample data points if no history exists
                return self._generate_sample_price_history(pool_id, hours)
            
            # Get price points for the specified number of hours
            cutoff_time = time.time() - (hours * 60 * 60)
            recent_prices = [(p[0], p[1]) for p in self.price_history[pool_id] if p[0] >= cutoff_time]
            
            # Format for frontend
            return [
                {
                    "timestamp": datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S"),
                    "price": price
                } for timestamp, price in recent_prices
            ]
        except Exception as e:
            logger.error(f"Error getting recent price history: {str(e)}")
            return self._generate_sample_price_history(pool_id, hours)
    
    def _generate_sample_price_history(self, pool_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Generate sample price history if real data is not available"""
        try:
            current_price = self.dex_trading.pools[pool_id]["current_price"]
            price_history = []
            
            # Generate one data point per hour
            for hour in range(hours, 0, -1):
                timestamp = time.time() - (hour * 60 * 60)
                # Add some randomness to the price
                random_factor = random.uniform(0.98, 1.02)  # +/- 2% randomness
                price = current_price * random_factor * (1 + (hours - hour) * 0.001)  # Small trend
                
                price_history.append({
                    "timestamp": datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S"),
                    "price": price
                })
            
            # Add current price
            price_history.append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "price": current_price
            })
            
            return price_history
        except Exception as e:
            logger.error(f"Error generating sample price history: {str(e)}")
            return []
    
    async def get_pool_metrics(self, pool_id: str) -> Dict[str, Any]:
        """Get real-time metrics for a pool including recent trades"""
        try:
            if pool_id not in self.dex_trading.pools:
                logger.error(f"Pool {pool_id} not found")
                return {}
            
            # Get recent trades
            recent_trades = await self.dex_trading.get_trades(pool_id, limit=20)
            
            # Calculate order book metrics
            order_book = await self.dex_trading.get_order_book(pool_id)
            order_book_metrics = self._calculate_order_book_metrics(order_book)
            
            # Calculate price impact for different trade sizes
            price_impact = self._calculate_price_impact_metrics(pool_id, order_book)
            
            return {
                "pool_id": pool_id,
                "recent_trades": recent_trades,
                "order_book_metrics": order_book_metrics,
                "price_impact": price_impact
            }
        except Exception as e:
            logger.error(f"Error getting pool metrics: {str(e)}")
            return {}
    
    def _calculate_order_book_metrics(self, order_book: Dict[str, Any]) -> Dict[str, float]:
        """Calculate metrics from the order book"""
        try:
            if not order_book or "buy_orders" not in order_book or "sell_orders" not in order_book:
                return {
                    "bid_ask_spread": 0.0,
                    "bid_ask_spread_percent": 0.0,
                    "book_depth_buys": 0.0,
                    "book_depth_sells": 0.0,
                    "midpoint_price": 0.0
                }
            
            buy_orders = order_book.get("buy_orders", [])
            sell_orders = order_book.get("sell_orders", [])
            
            # Calculate best bid and ask
            best_bid = buy_orders[0]["price"] if buy_orders else 0.0
            best_ask = sell_orders[0]["price"] if sell_orders else 0.0
            
            # Calculate spread
            bid_ask_spread = best_ask - best_bid if best_bid > 0 and best_ask > 0 else 0.0
            midpoint_price = (best_bid + best_ask) / 2 if best_bid > 0 and best_ask > 0 else 0.0
            bid_ask_spread_percent = (bid_ask_spread / midpoint_price) * 100 if midpoint_price > 0 else 0.0
            
            # Calculate book depth (total value of orders)
            book_depth_buys = sum(order["amount"] * order["price"] for order in buy_orders)
            book_depth_sells = sum(order["amount"] * order["price"] for order in sell_orders)
            
            return {
                "bid_ask_spread": bid_ask_spread,
                "bid_ask_spread_percent": bid_ask_spread_percent,
                "book_depth_buys": book_depth_buys,
                "book_depth_sells": book_depth_sells,
                "midpoint_price": midpoint_price
            }
        except Exception as e:
            logger.error(f"Error calculating order book metrics: {str(e)}")
            return {
                "bid_ask_spread": 0.0,
                "bid_ask_spread_percent": 0.0,
                "book_depth_buys": 0.0,
                "book_depth_sells": 0.0,
                "midpoint_price": 0.0
            }
    
    def _calculate_price_impact_metrics(self, pool_id: str, order_book: Dict[str, Any]) -> Dict[str, List[Dict[str, float]]]:
        """Calculate price impact for different trade sizes"""
        try:
            if not order_book or "buy_orders" not in order_book or "sell_orders" not in order_book:
                return {
                    "buy": [],
                    "sell": []
                }
            
            current_price = self.dex_trading.pools[pool_id]["current_price"]
            buy_orders = order_book.get("buy_orders", [])
            sell_orders = order_book.get("sell_orders", [])
            
            # Define trade sizes to analyze (as percentage of pool liquidity)
            trade_sizes = [0.001, 0.005, 0.01, 0.05, 0.1]  # 0.1% to 10%
            pool_liquidity = self._estimate_pool_liquidity(pool_id)
            
            # Calculate price impact for buys (selling into the order book)
            buy_impacts = []
            for size_pct in trade_sizes:
                trade_value = pool_liquidity * size_pct
                price_after = self._simulate_trade_price("buy", trade_value, sell_orders)
                impact_pct = ((price_after - current_price) / current_price) * 100
                buy_impacts.append({
                    "size": trade_value,
                    "size_percent": size_pct * 100,
                    "price_after": price_after,
                    "impact_percent": impact_pct
                })
            
            # Calculate price impact for sells (selling into the order book)
            sell_impacts = []
            for size_pct in trade_sizes:
                trade_value = pool_liquidity * size_pct
                price_after = self._simulate_trade_price("sell", trade_value, buy_orders)
                impact_pct = ((current_price - price_after) / current_price) * 100
                sell_impacts.append({
                    "size": trade_value,
                    "size_percent": size_pct * 100,
                    "price_after": price_after,
                    "impact_percent": impact_pct
                })
            
            return {
                "buy": buy_impacts,
                "sell": sell_impacts
            }
        except Exception as e:
            logger.error(f"Error calculating price impact metrics: {str(e)}")
            return {
                "buy": [],
                "sell": []
            }
    
    def _simulate_trade_price(self, side: str, trade_value: float, orders: List[Dict[str, float]]) -> float:
        """Simulate the price after executing a trade of given value"""
        try:
            if not orders:
                return 0.0
            
            remaining_value = trade_value
            total_quantity_filled = 0.0
            price_impact = 0.0
            
            for order in orders:
                order_price = order["price"]
                order_amount = order["amount"]
                order_value = order_price * order_amount
                
                if remaining_value <= order_value:
                    # This order can fill the remaining trade value
                    filled_amount = remaining_value / order_price
                    total_quantity_filled += filled_amount
                    remaining_value = 0.0
                    break
                else:
                    # This order will be completely filled
                    total_quantity_filled += order_amount
                    remaining_value -= order_value
            
            # Calculate weighted average price of filled orders
            if total_quantity_filled > 0:
                return trade_value / total_quantity_filled
            else:
                # If no orders were filled, return the best available price
                return orders[0]["price"]
        except Exception as e:
            logger.error(f"Error simulating trade price: {str(e)}")
            return 0.0

import asyncio
from typing import Dict, List, Optional
from loguru import logger
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from .dex_trading import DexTrading

class DexAnalytics:
    def __init__(self, dex_trading: DexTrading):
        self.dex = dex_trading
        self.metrics: Dict[str, Dict] = {}
        self.trade_history: Dict[str, List[Dict]] = {}
        self.price_history: Dict[str, List[Dict]] = {}
        self.volume_history: Dict[str, List[Dict]] = {}

    async def track_pool_metrics(self, pool_id: str):
        """Start tracking metrics for a pool"""
        try:
            if pool_id not in self.metrics:
                self.metrics[pool_id] = {
                    "total_volume": 0.0,
                    "total_trades": 0,
                    "avg_trade_size": 0.0,
                    "price_volatility": 0.0,
                    "liquidity_depth": 0.0,
                    "last_update": datetime.now()
                }
                
                # Initialize history
                self.trade_history[pool_id] = []
                self.price_history[pool_id] = []
                self.volume_history[pool_id] = []
                
                # Start tracking loop
                asyncio.create_task(self._track_pool_loop(pool_id))
                
        except Exception as e:
            logger.error(f"Error starting pool tracking: {str(e)}")

    async def _track_pool_loop(self, pool_id: str):
        """Background loop for tracking pool metrics"""
        try:
            while True:
                # Get current pool state
                pool_state = await self.dex.get_pool_state(pool_id)
                order_book = await self.dex.get_order_book(pool_id)
                
                if pool_state and order_book:
                    # Update metrics
                    await self._update_pool_metrics(pool_id, pool_state, order_book)
                
                # Wait for next update
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error in pool tracking loop: {str(e)}")

    async def _update_pool_metrics(self, pool_id: str, pool_state: Dict, order_book: Dict):
        """Update pool metrics with latest data"""
        try:
            metrics = self.metrics[pool_id]
            
            # Update price history
            self.price_history[pool_id].append({
                "timestamp": datetime.now(),
                "price": pool_state["current_price"]
            })
            
            # Update volume history
            total_volume = sum(order["amount"] for order in order_book["buy_orders"] + order_book["sell_orders"])
            self.volume_history[pool_id].append({
                "timestamp": datetime.now(),
                "volume": total_volume
            })
            
            # Calculate metrics
            metrics["total_volume"] = sum(entry["volume"] for entry in self.volume_history[pool_id])
            metrics["total_trades"] = len(self.trade_history[pool_id])
            metrics["avg_trade_size"] = metrics["total_volume"] / metrics["total_trades"] if metrics["total_trades"] > 0 else 0
            metrics["price_volatility"] = self._calculate_volatility(pool_id)
            metrics["liquidity_depth"] = self._calculate_liquidity_depth(order_book)
            metrics["last_update"] = datetime.now()
            
        except Exception as e:
            logger.error(f"Error updating pool metrics: {str(e)}")

    def _calculate_volatility(self, pool_id: str) -> float:
        """Calculate price volatility"""
        try:
            if len(self.price_history[pool_id]) < 2:
                return 0.0
            
            prices = np.array([entry["price"] for entry in self.price_history[pool_id]])
            returns = np.diff(prices) / prices[:-1]
            return np.std(returns)
            
        except Exception as e:
            logger.error(f"Error calculating volatility: {str(e)}")
            return 0.0

    def _calculate_liquidity_depth(self, order_book: Dict) -> float:
        """Calculate liquidity depth"""
        try:
            # Calculate total liquidity in order book
            buy_liquidity = sum(order["amount"] * order["price"] for order in order_book["buy_orders"])
            sell_liquidity = sum(order["amount"] * order["price"] for order in order_book["sell_orders"])
            
            return buy_liquidity + sell_liquidity
            
        except Exception as e:
            logger.error(f"Error calculating liquidity depth: {str(e)}")
            return 0.0

    async def get_pool_metrics(self, pool_id: str) -> Dict:
        """Get current metrics for a pool"""
        try:
            if pool_id not in self.metrics:
                return None
            
            return self.metrics[pool_id]
            
        except Exception as e:
            logger.error(f"Error getting pool metrics: {str(e)}")
            return None

    async def get_pool_analytics(self, pool_id: str, timeframe: str = "24h") -> Dict:
        """Get detailed analytics for a pool"""
        try:
            if pool_id not in self.metrics:
                return None
            
            # Calculate timeframe
            now = datetime.now()
            if timeframe == "24h":
                start_time = now - timedelta(hours=24)
            elif timeframe == "7d":
                start_time = now - timedelta(days=7)
            elif timeframe == "30d":
                start_time = now - timedelta(days=30)
            else:
                start_time = now - timedelta(hours=24)
            
            # Filter history data
            price_data = [entry for entry in self.price_history[pool_id] if entry["timestamp"] >= start_time]
            volume_data = [entry for entry in self.volume_history[pool_id] if entry["timestamp"] >= start_time]
            
            # Calculate analytics
            analytics = {
                "timeframe": timeframe,
                "price_stats": {
                    "current": price_data[-1]["price"] if price_data else 0,
                    "high": max(entry["price"] for entry in price_data) if price_data else 0,
                    "low": min(entry["price"] for entry in price_data) if price_data else 0,
                    "avg": np.mean([entry["price"] for entry in price_data]) if price_data else 0,
                    "volatility": self._calculate_volatility(pool_id)
                },
                "volume_stats": {
                    "total": sum(entry["volume"] for entry in volume_data),
                    "avg": np.mean([entry["volume"] for entry in volume_data]) if volume_data else 0,
                    "max": max(entry["volume"] for entry in volume_data) if volume_data else 0
                },
                "liquidity_stats": {
                    "current_depth": self.metrics[pool_id]["liquidity_depth"],
                    "avg_depth": np.mean([self._calculate_liquidity_depth(entry) for entry in volume_data]) if volume_data else 0
                }
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error getting pool analytics: {str(e)}")
            return None

    async def get_market_overview(self) -> Dict:
        """Get overview of all tracked pools"""
        try:
            overview = {
                "total_pools": len(self.metrics),
                "total_volume_24h": sum(self.metrics[pool_id]["total_volume"] for pool_id in self.metrics),
                "total_trades_24h": sum(self.metrics[pool_id]["total_trades"] for pool_id in self.metrics),
                "pools": {}
            }
            
            for pool_id in self.metrics:
                overview["pools"][pool_id] = {
                    "volume_24h": self.metrics[pool_id]["total_volume"],
                    "trades_24h": self.metrics[pool_id]["total_trades"],
                    "avg_trade_size": self.metrics[pool_id]["avg_trade_size"],
                    "price_volatility": self.metrics[pool_id]["price_volatility"],
                    "liquidity_depth": self.metrics[pool_id]["liquidity_depth"]
                }
            
            return overview
            
        except Exception as e:
            logger.error(f"Error getting market overview: {str(e)}")
            return None 