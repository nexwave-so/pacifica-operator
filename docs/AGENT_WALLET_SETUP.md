# Pacifica Agent Wallet Setup

## ⚠️ Important: Two Different Keys Required

Pacifica API requires **TWO separate keys**:

### 1. API Key (from Pacifica UI)
- **What it is**: Authentication key from Pacifica UI → API Settings
- **Environment Variable**: `PACIFICA_API_KEY`
- **Current Value**: `<your_api_key>` ✅
- **Used for**: `X-API-Key` header in API requests

### 2. Agent Wallet Keypair (Must be Generated)
- **What it is**: A Solana keypair generated specifically for API signing
- **Environment Variables**: 
  - `PACIFICA_AGENT_WALLET_PRIVKEY` - Private key (~88 chars base58)
  - `PACIFICA_AGENT_WALLET_PUBKEY` - Public key
- **Current Issue**: The value in `PACIFICA_AGENT_WALLET_PRIVKEY` appears to be the API key, not an agent wallet
- **Used for**: Signing order transactions

## How to Generate Agent Wallet

### Option 1: From Pacifica UI (Recommended)

1. Go to Pacifica UI → API Settings
2. Look for "Agent Wallet" or "API Agent Key" section
3. Generate/create a new Agent Wallet
4. Copy the **private key** (full keypair, ~88 characters)
5. Copy the **public key**

### Option 2: Generate Using Python

```python
from solders.keypair import Keypair
import base58

# Generate new keypair
keypair = Keypair()

# Get private key (full keypair in base58 - ~88 chars)
privkey = base58.b58encode(bytes(keypair)).decode()
print(f"Private Key: {privkey}")

# Get public key
pubkey = str(keypair.pubkey())
print(f"Public Key: {pubkey}")
```

Then:
1. Register this public key in Pacifica UI as an Agent Wallet
2. Update `.env` with both keys

### Option 3: If You Have a 32-byte Seed

If `<your_private_key>` is a valid 32-byte seed:
- The code will attempt to convert it (requires PyNaCl)
- Verify the derived public key matches: `<your_public_key>`

## Current Configuration Check

```bash
# Check what's in .env
grep PACIFICA .env

# Should see:
# PACIFICA_API_KEY=<your_api_key>  ✅ API Key
# PACIFICA_AGENT_WALLET_PRIVKEY=...  ❓ Should be ~88 char Solana keypair
# PACIFICA_AGENT_WALLET_PUBKEY=<your_public_key>  ✅
```

## Verification

After setting up the Agent Wallet correctly:

1. **Restart services**:
   ```bash
   docker compose restart order-management
   ```

2. **Check logs**:
   ```bash
   docker compose logs order-management | grep "Initialized Pacifica"
   ```
   
   Should see: `Initialized Pacifica client with wallet: <your_public_key>`

3. **Test connection**:
   - The service should start without "TooShort" errors
   - Should be able to fetch positions
   - Should be able to place orders

## References

- [Pacifica API Agent Keys Docs](https://docs.pacifica.fi/api-documentation/api/signing/api-agent-keys)
- [Pacifica Signing Documentation](https://docs.pacifica.fi/api-documentation/api/signing)

