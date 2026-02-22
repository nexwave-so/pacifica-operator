# Security Guidelines

## Private Keys and Secrets

**NEVER** display, log, or print:
- Private keys (`PACIFICA_AGENT_WALLET_PRIVKEY`)
- API keys (`PACIFICA_API_KEY`)
- Database passwords
- JWT secrets
- Any other sensitive credentials

## Logging Best Practices

1. **Never log private keys or secrets**
   - Only check if they're set (boolean checks)
   - Never print the actual values

2. **Sanitize error messages**
   - Truncate error messages to avoid exposing sensitive data
   - Use debug-level logging for detailed errors
   - Only log status codes in production

3. **API responses**
   - Don't log full API responses in production
   - Truncate error responses to first 200 characters
   - Use debug-level logging for detailed responses

4. **Request data**
   - Don't log full request payloads that contain signatures
   - Only log order IDs, symbols, amounts (not sensitive)

## Example Safe Patterns

```python
# ✅ GOOD - Only check if set
has_privkey = bool(settings.pacifica_agent_wallet_privkey)
print(f"Wallet Privkey: {'✅ Set' if has_privkey else '❌ Not set'}")

# ❌ BAD - Never do this
print(f"Private key: {settings.pacifica_agent_wallet_privkey}")

# ✅ GOOD - Sanitized error
logger.error(f"API error: {response.status_code}")
logger.debug(f"Error details: {response.text[:200]}")

# ❌ BAD - Never do this
logger.error(f"Full response: {response.text}")
```

## Environment Variables

All sensitive data should be in environment variables, never in code:
- `.env` files should not be committed to git
- Use `.env.example` with placeholder values
- Document required variables in `env.example`

## Live Streaming / Screen Sharing

When streaming or sharing your screen:
1. Use paper trading mode when possible
2. Never show `.env` files
3. Use test scripts that don't display secrets
4. Check logs before sharing to ensure no secrets are visible

