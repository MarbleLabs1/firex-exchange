import os
import json
import time
import asyncio
import random
import numpy as np
from typing import Dict, Any, List, Optional
from decimal import Decimal
from loguru import logger
from datetime import datetime, timedelta

class MarketMaker:
    """Provides market making strategies for the DEX"""
    
    def __init__(self, dex_trading):
        self.dex_trading = dex_trading
        self.strategies = {}
        self.running = False
        self.task = None
        self.price_history = {}
        self.volume_history = {}
    
    async def start_service(self) -> bool:
        """Start the market making service"""
        try:
            if self.running:
                return True
            
            self.running = True
            self.task = asyncio.create_task(self._market_making_loop())
            
            logger.info("Market making service started")
            return True
        except Exception as e:
            logger.error(f"Error starting market making service: {str(e)}")
            return False
    
    async def stop_service(self) -> bool:
        """Stop the market making service"""
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
            
            logger.info("Market making service stopped")
            return True
        except Exception as e:
            logger.error(f"Error stopping market making service: {str(e)}")
            return False
    
    async def start_strategy(self, pool_id: str, strategy_type: str, params: Dict[str, Any]) -> Optional[str]:
        """Start a market making strategy"""
        try:
            # Validate pool exists
            pools = await self.dex_trading.get_pools()
            if pool_id not in pools:
                logger.error(f"Pool {pool_id} not found")
                return None
            
            # Validate strategy type
            valid_strategies = ["constant_spread", "adaptive_spread", "mean_reversion"]
            if strategy_type not in valid_strategies:
                logger.error(f"Invalid strategy type: {strategy_type}")
                return None
            
            # Create strategy ID
            strategy_id = f"{strategy_type}_{pool_id}_{int(time.time())}"
            
            # Initialize strategy
            self.strategies[strategy_id] = {
                "id": strategy_id,
                "pool_id": pool_id,
                "type": strategy_type,
                "params": params,
                "status": "active",
                "orders": [],
                "created_at": time.time(),
                "last_update": time.time()
            }
            
            # Start the strategy loop if not already running
            if not self.running:
                await self.start_service()
            
            logger.info(f"Started {strategy_type} strategy for pool {pool_id}")
            return strategy_id
        except Exception as e:
            logger.error(f"Error starting strategy: {str(e)}")
            return None
    
    async def stop_strategy(self, strategy_id: str) -> bool:
        """Stop a market making strategy"""
        try:
            if strategy_id not in self.strategies:
                logger.error(f"Strategy {strategy_id} not found")
                return False
            
            # Cancel all active orders for this strategy
            for order_id in self.strategies[strategy_id]["orders"]:
                await self.dex_trading.cancel_order(order_id)
            
            # Update strategy status
            self.strategies[strategy_id]["status"] = "stopped"
            self.strategies[strategy_id]["last_update"] = time.time()
            
            logger.info(f"Stopped strategy {strategy_id}")
            return True
        except Exception as e:
            logger.error(f"Error stopping strategy: {str(e)}")
            return False
    
    async def get_strategy(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Get details about a specific strategy"""
        try:
            if strategy_id not in self.strategies:
                logger.error(f"Strategy {strategy_id} not found")
                return None
            
            return self.strategies[strategy_id]
        except Exception as e:
            logger.error(f"Error getting strategy: {str(e)}")
            return None
    
    async def get_strategies(self, pool_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all active strategies"""
        try:
            result = []
            for strategy in self.strategies.values():
                if pool_id is None or strategy["pool_id"] == pool_id:
                    result.append(strategy)
            return result
        except Exception as e:
            logger.error(f"Error getting strategies: {str(e)}")
            return []
    
    async def _market_making_loop(self):
        """Background task to execute market making strategies"""
        while self.running:
            try:
                # Process all active strategies
                for strategy_id, strategy in list(self.strategies.items()):
                    if strategy["status"] != "active":
                        continue
                    
                    # Execute strategy based on type
                    if strategy["type"] == "constant_spread":
                        await self._execute_constant_spread(strategy_id)
                    elif strategy["type"] == "adaptive_spread":
                        await self._execute_adaptive_spread(strategy_id)
                    elif strategy["type"] == "mean_reversion":
                        await self._execute_mean_reversion(strategy_id)
                    
                    # Update last update timestamp
                    self.strategies[strategy_id]["last_update"] = time.time()
                
                # Sleep to avoid excessive API calls
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in market making loop: {str(e)}")
                await asyncio.sleep(5)
    
    def _update_market_data(self, pool_id: str, price: float, volume: float):
        """Update price and volume history"""
        if pool_id not in self.price_history:
            self.price_history[pool_id] = []
            self.volume_history[pool_id] = []
        
        self.price_history[pool_id].append(price)
        self.volume_history[pool_id].append(volume)
        
        # Keep only last 1000 data points
        max_history = 1000
        if len(self.price_history[pool_id]) > max_history:
            self.price_history[pool_id] = self.price_history[pool_id][-max_history:]
            self.volume_history[pool_id] = self.volume_history[pool_id][-max_history:]

    def _calculate_volatility(self, pool_id: str) -> float:
        """Calculate price volatility"""
        if pool_id not in self.price_history or len(self.price_history[pool_id]) < 2:
            return 0.0
        
        prices = np.array(self.price_history[pool_id])
        returns = np.diff(prices) / prices[:-1]
        return np.std(returns)

    def _calculate_mean_price(self, pool_id: str) -> float:
        """Calculate mean price"""
        if pool_id not in self.price_history:
            return 0.0
        
        return np.mean(self.price_history[pool_id])

    def _calculate_depth_multiplier(self, order_book: Dict) -> float:
        """Calculate order size multiplier based on market depth"""
        try:
            # Calculate total volume in order book
            total_volume = sum(order["amount"] for order in order_book["buy_orders"] + order_book["sell_orders"])
            
            # Normalize to get multiplier
            base_volume = 1000  # Arbitrary base volume
            return min(max(total_volume / base_volume, 0.5), 2.0)
            
        except Exception as e:
            logger.error(f"Error calculating depth multiplier: {str(e)}")
            return 1.0
    
    async def _execute_constant_spread(self, strategy_id: str):
        """Execute constant spread market making strategy"""
        try:
            strategy = self.strategies[strategy_id]
            pool_id = strategy["pool_id"]
            
            # Get order book to determine current price
            order_book = await self.dex_trading.get_order_book(pool_id)
            if not order_book:
                return
            
            # Get the midpoint price
            current_price = self.dex_trading.pools[pool_id]["current_price"]
            
            # Get strategy parameters
            base_size = Decimal(str(strategy["params"].get("base_size", 1.0)))
            spread = Decimal(str(strategy["params"].get("spread", 0.01)))  # 1% spread
            
            # Calculate buy and sell prices
            buy_price = current_price * (Decimal("1") - spread)
            sell_price = current_price * (Decimal("1") + spread)
            
            # Cancel existing orders for this strategy
            for order_id in strategy["orders"]:
                await self.dex_trading.cancel_order(order_id)
            
            # Clear order list
            strategy["orders"] = []
            
            # Place new buy order
            buy_order_id = await self.dex_trading.create_order(
                pool_id=pool_id,
                side="buy",
                amount=base_size,
                price=buy_price,
                slippage=Decimal("0.005"),  # 0.5% slippage
                metadata={"strategy_id": strategy_id}
            )
            
            if buy_order_id:
                strategy["orders"].append(buy_order_id)
            
            # Place new sell order
            sell_order_id = await self.dex_trading.create_order(
                pool_id=pool_id,
                side="sell",
                amount=base_size,
                price=sell_price,
                slippage=Decimal("0.005"),  # 0.5% slippage
                metadata={"strategy_id": strategy_id}
            )
            
            if sell_order_id:
                strategy["orders"].append(sell_order_id)
            
            logger.info(f"Executed constant spread strategy for {pool_id}: Buy @ {buy_price}, Sell @ {sell_price}")
        except Exception as e:
            logger.error(f"Error executing constant spread strategy: {str(e)}")
    
    async def _execute_adaptive_spread(self, strategy_id: str):
        """Execute adaptive spread market making strategy"""
        try:
            strategy = self.strategies[strategy_id]
            pool_id = strategy["pool_id"]
            
            # Get order book to determine current price and volatility
            order_book = await self.dex_trading.get_order_book(pool_id)
            if not order_book:
                return
            
            # Get the midpoint price
            current_price = self.dex_trading.pools[pool_id]["current_price"]
            
            # Update market data for volatility calculation
            self._update_market_data(pool_id, current_price, 
                                    sum(order["amount"] for order in order_book["buy_orders"] + order_book["sell_orders"]))
            
            # Get strategy parameters
            base_size = Decimal(str(strategy["params"].get("base_size", 1.0)))
            min_spread = Decimal(str(strategy["params"].get("min_spread", 0.005)))  # 0.5% minimum spread
            max_spread = Decimal(str(strategy["params"].get("max_spread", 0.03)))  # 3% maximum spread
            
            # Calculate volatility
            volatility = Decimal(str(self._calculate_volatility(pool_id)))
            
            # Calculate adaptive spread based on volatility
            spread = min(max(min_spread, volatility * Decimal("10")), max_spread)
            
            # Calculate buy and sell prices
            buy_price = current_price * (Decimal("1") - spread)
            sell_price = current_price * (Decimal("1") + spread)
            
            # Calculate order size multiplier based on market depth
            depth_multiplier = Decimal(str(self._calculate_depth_multiplier(order_book)))
            adjusted_size = base_size * depth_multiplier
            
            # Cancel existing orders for this strategy
            for order_id in strategy["orders"]:
                await self.dex_trading.cancel_order(order_id)
            
            # Clear order list
            strategy["orders"] = []
            
            # Place new buy order
            buy_order_id = await self.dex_trading.create_order(
                pool_id=pool_id,
                side="buy",
                amount=adjusted_size,
                price=buy_price,
                slippage=Decimal("0.005"),  # 0.5% slippage
                metadata={"strategy_id": strategy_id}
            )
            
            if buy_order_id:
                strategy["orders"].append(buy_order_id)
            
            # Place new sell order
            sell_order_id = await self.dex_trading.create_order(
                pool_id=pool_id,
                side="sell",
                amount=adjusted_size,
                price=sell_price,
                slippage=Decimal("0.005"),  # 0.5% slippage
                metadata={"strategy_id": strategy_id}
            )
            
            if sell_order_id:
                strategy["orders"].append(sell_order_id)
            
            logger.info(f"Executed adaptive spread strategy for {pool_id}: Buy @ {buy_price}, Sell @ {sell_price}, Spread: {float(spread)*100:.2f}%")
        except Exception as e:
            logger.error(f"Error executing adaptive spread strategy: {str(e)}")
    
    async def _execute_mean_reversion(self, strategy_id: str):
        """Execute mean reversion market making strategy"""
        try:
            strategy = self.strategies[strategy_id]
            pool_id = strategy["pool_id"]
            
            # Get order book to get current price
            order_book = await self.dex_trading.get_order_book(pool_id)
            if not order_book:
                return
            
            # Get current price
            current_price = self.dex_trading.pools[pool_id]["current_price"]
            
            # Update market data for mean price calculation
            self._update_market_data(pool_id, current_price, 
                                    sum(order["amount"] for order in order_book["buy_orders"] + order_book["sell_orders"]))
            
            # Get strategy parameters
            base_size = Decimal(str(strategy["params"].get("base_size", 1.0)))
            target_price = Decimal(str(strategy["params"].get("target_price", self._calculate_mean_price(pool_id))))
            reversion_factor = Decimal(str(strategy["params"].get("reversion_factor", 0.1)))  # Strength of reversion
            
            # Calculate price deviation from target
            if target_price == 0:
                deviation = Decimal("0")
            else:
                deviation = (current_price - target_price) / target_price
            
            # Adjust order sizes based on deviation (mean reversion)
            # If price is above target, buy less and sell more
            # If price is below target, buy more and sell less
            buy_size = base_size * (Decimal("1") - deviation * reversion_factor)
            sell_size = base_size * (Decimal("1") + deviation * reversion_factor)
            
            # Ensure minimum order size
            min_size = Decimal("0.1")
            buy_size = max(buy_size, min_size)
            sell_size = max(sell_size, min_size)
            
            # Calculate prices with a fixed spread
            spread = Decimal("0.01")  # 1% spread
            buy_price = current_price * (Decimal("1") - spread/Decimal("2"))
            sell_price = current_price * (Decimal("1") + spread/Decimal("2"))
            
            # Cancel existing orders for this strategy
            for order_id in strategy["orders"]:
                await self.dex_trading.cancel_order(order_id)
            
            # Clear order list
            strategy["orders"] = []
            
            # Place new buy order
            buy_order_id = await self.dex_trading.create_order(
                pool_id=pool_id,
                side="buy",
                amount=buy_size,
                price=buy_price,
                slippage=Decimal("0.005"),  # 0.5% slippage
                metadata={"strategy_id": strategy_id}
            )
            
            if buy_order_id:
                strategy["orders"].append(buy_order_id)
            
            # Place new sell order
            sell_order_id = await self.dex_trading.create_order(
                pool_id=pool_id,
                side="sell",
                amount=sell_size,
                price=sell_price,
                slippage=Decimal("0.005"),  # 0.5% slippage
                metadata={"strategy_id": strategy_id}
            )
            
            if sell_order_id:
                strategy["orders"].append(sell_order_id)
            
            logger.info(f"Executed mean reversion strategy for {pool_id}: Buy {float(buy_size):.4f} @ {buy_price}, Sell {float(sell_size):.4f} @ {sell_price}")
        except Exception as e:
            logger.error(f"Error executing mean reversion strategy: {str(e)}")
