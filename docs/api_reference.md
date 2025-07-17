# DEX Blockchain API Reference

## Overview

This document describes the internal API interfaces for the DEX Blockchain project. These APIs can be used for extending functionality or integrating with other systems.

## Blockchain API

### `blockchain_core.BlockchainCore`

#### Methods

```python
connect(endpoint: str) -> bool
```
Establishes connection to the blockchain network.
- **Parameters:** `endpoint` - RPC endpoint URL
- **Returns:** Boolean indicating success

```python
create_account() -> dict
```
Creates a new blockchain account/wallet.
- **Returns:** Dictionary with keys: `public_key`, `private_key`, `mnemonic`

```python
load_account(private_key: str) -> dict
```
Loads an existing account from private key.
- **Parameters:** `private_key` - Account private key
- **Returns:** Dictionary with account information

```python
get_balance(address: str) -> float
```
Returns the balance for a given address.
- **Parameters:** `address` - Account address
- **Returns:** Balance as float

```python
send_transaction(from_address: str, to_address: str, amount: float, private_key: str) -> str
```
Sends a transaction on the blockchain.
- **Parameters:**
  - `from_address` - Sender address
  - `to_address` - Recipient address
  - `amount` - Amount to send
  - `private_key` - Sender's private key
- **Returns:** Transaction hash

## Trading API

### `dex_trading.TradingEngine`

#### Methods

```python
create_order(user_id: str, order_type: str, side: str, price: float, amount: float, pair: str) -> str
```
Creates a new trading order.
- **Parameters:**
  - `user_id` - User identifier
  - `order_type` - "market" or "limit"
  - `side` - "buy" or "sell"
  - `price` - Order price (for limit orders)
  - `amount` - Order amount
  - `pair` - Trading pair (e.g., "SOL/USDC")
- **Returns:** Order ID

```python
cancel_order(order_id: str, user_id: str) -> bool
```
Cancels an existing order.
- **Parameters:**
  - `order_id` - ID of order to cancel
  - `user_id` - User who owns the order
- **Returns:** Boolean indicating success

```python
get_order_book(pair: str, depth: int = 10) -> dict
```
Retrieves the current order book for a trading pair.
- **Parameters:**
  - `pair` - Trading pair
  - `depth` - Number of levels to return
- **Returns:** Dictionary with "bids" and "asks" lists

## Analytics API

### `dex_analytics.AnalyticsEngine`

#### Methods

```python
get_price_history(pair: str, timeframe: str, start_time: int, end_time: int) -> list
```
Returns historical price data.
- **Parameters:**
  - `pair` - Trading pair
  - `timeframe` - Candle timeframe (e.g., "1m", "1h", "1d")
  - `start_time` - Start timestamp
  - `end_time` - End timestamp
- **Returns:** List of OHLCV candles

```python
calculate_indicator(indicator: str, pair: str, timeframe: str, **params) -> list
```
Calculates technical indicator values.
- **Parameters:**
  - `indicator` - Indicator name (e.g., "RSI", "MACD")
  - `pair` - Trading pair
  - `timeframe` - Candle timeframe
  - `params` - Indicator-specific parameters
- **Returns:** List of indicator values

## Wallet API

### `wallet.WalletManager`

#### Methods

```python
create_wallet(user_id: str) -> dict
```
Creates a new wallet for a user.
- **Parameters:** `user_id` - User identifier
- **Returns:** Wallet information dictionary

```python
get_balances(wallet_id: str) -> dict
```
Returns all token balances for a wallet.
- **Parameters:** `wallet_id` - Wallet identifier
- **Returns:** Dictionary mapping token symbols to balances

```python
transfer(from_wallet: str, to_address: str, token: str, amount: float) -> str
```
Transfers tokens from a wallet to an address.
- **Parameters:**
  - `from_wallet` - Source wallet ID
  - `to_address` - Destination address
  - `token` - Token symbol
  - `amount` - Amount to transfer
- **Returns:** Transaction hash

## Event System

### `utils.events.EventBus`

#### Methods

```python
subscribe(event_type: str, callback: callable) -> str
```
Subscribes to an event type.
- **Parameters:**
  - `event_type` - Type of event to subscribe to
  - `callback` - Function to call when event occurs
- **Returns:** Subscription ID

```python
unsubscribe(subscription_id: str) -> bool
```
Removes a subscription.
- **Parameters:** `subscription_id` - ID of subscription to remove
- **Returns:** Boolean indicating success

```python
publish(event_type: str, data: dict) -> None
```
Publishes an event.
- **Parameters:**
  - `event_type` - Type of event
  - `data` - Event data

