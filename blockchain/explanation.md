# Understanding the Marble Blockchain: Tokens vs. Coins and Mining Implementation

## Why Your Wallet Shows 1.0 Coins Instead of 1000 Tokens

After analyzing your blockchain implementation, I can explain why you see a balance of 1.0 coins despite minting 1000 tokens. The key issue is that **your blockchain has two separate currency systems** working in parallel:

### 1. Dual-Currency Architecture

- **Native Coins**: Similar to ETH on Ethereum, these are the blockchain's fundamental currency used for transaction fees and mining rewards
- **Tokens**: Similar to ERC-20 tokens on Ethereum or SPL tokens on Solana, these are created through the minting process

When you check your wallet balance with option 3, you're only seeing the native coin balance (1.0 coins), which comes from the mining reward. The 1000 tokens you minted are stored in a separate token account system.

### 2. How Tokens and Native Coins Are Separately Implemented

Looking at the code:

```python
# In the BlockchainNode class:
# Native coins are tracked in the blockchain directly
def get_address_balance(self, address: str) -> float:
    balance = 0
    for block in self.chain:
        for tx in block.transactions:
            if tx.recipient == address:
                balance += tx.amount
            if tx.sender == address:
                balance -= (tx.amount + tx.fee)
    return balance

# Tokens are tracked in separate token accounts
def mint_tokens(self, authority: str, recipient: str, amount: float) -> bool:
    # Create token mint and token account...
    recipient_account = self.create_token_account(recipient, mint_address)
    recipient_account.balance += amount
```

The `token_accounts` dictionary stores token balances, but the `get_balance()` function only returns native coin balances. There's no UI option to view token balances, which is why you only see the 1.0 coins from mining and not your 1000 minted tokens.

### 3. Mining Implementation vs. Professional Blockchains

Your current implementation uses a simple Proof of Work (PoW) approach:

```python
def mine_block(self, difficulty: int) -> None:
    target = "0" * difficulty
    while self.hash[:difficulty] != target:
        self.nonce += 1
        self.hash = self.calculate_hash()
```

This differs significantly from major blockchains:

#### Solana
- Uses **Proof of History (PoH)** combined with **Proof of Stake (PoS)**
- PoH provides a historical record that proves events occurred at a specific time
- Achieves high throughput (65,000+ TPS) through parallel transaction processing
- Has a leader schedule where validators take turns producing blocks
- Mining and minting are completely separate concepts

#### Binance Chain
- Uses **Delegated Proof of Stake (DPoS)**
- Has a limited set of validator nodes elected by token holders
- Focuses on high throughput for exchange operations
- Clear separation between the native BNB coin and BEP-20/BEP-2 tokens

#### Ethereum
- Originally used PoW (like your implementation but far more complex)
- Transitioned to **Proof of Stake** with Ethereum 2.0
- Uses slashing conditions to penalize malicious validators
- Has a complex gas fee market for transaction processing
- Clear separation between ETH (native currency) and ERC-20 tokens

### 4. Recommended Improvements

To align your implementation with professional blockchain standards:

1. **Add Token Balance Display**:
   ```python
   def get_token_balance(self, address: str, mint_address: str) -> float:
       for account in self.token_accounts.values():
           if account.owner == address and account.mint_address == mint_address:
               return account.balance
       return 0.0
   ```

2. **Enhance the Wallet Info Display**:
   ```python
   # Modify the wallet info UI to show both native coins and tokens
   print(f"Native Balance: {balance:.6f} coins")
   for token_account in token_accounts:
       if token_account.owner == wallet.public_key:
           print(f"Token Balance: {token_account.balance} {token_mint.metadata['symbol']}")
   ```

3. **Implement a More Robust Consensus Mechanism**:
   - Consider adding a basic Proof of Stake implementation
   - Separate mining (consensus) from token creation (minting)
   - Add validator selection and rotation

4. **Improve Transaction Processing**:
   - Add parallel transaction validation
   - Implement a proper mempool for pending transactions
   - Add transaction prioritization based on fees

With these changes, your blockchain would more closely resemble professional implementations and would clearly display both your native coins (1.0) and minted tokens (1000).

