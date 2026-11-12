import requests

# Supported EVM chains (Alchemy network identifiers)
SUPPORTED_CHAINS = {
    "eth-mainnet": "Ethereum",
    "arb-mainnet": "Arbitrum",
    "opt-mainnet": "Optimism",
    "polygon-mainnet": "Polygon",
    "base-mainnet": "Base",
    "bnb-mainnet": "BNB Chain",
}


def fetch_wallet_chain_balance(api_key: str, address: str, chain_id: str) -> dict:
    """Fetches native and ERC-20 token balances with USD prices via Alchemy Portfolio API."""
    url = f"https://api.g.alchemy.com/data/v1/{api_key.strip()}/assets/tokens/by-address"
    payload = {
        "addresses": [
            {
                "address": address,
                "networks": [chain_id],
            }
        ],
        "withMetadata": True,
        "withPrices": True,
        "includeNativeTokens": True,
    }

    response = requests.post(url, json=payload, timeout=15)
    response.raise_for_status()
    data = response.json()

    tokens = data.get("data", {}).get("tokens", [])
    native_str = "0.0000"
    native_usd = 0.0
    tokens_usd = 0.0

    for item in tokens:
        raw_balance = item.get("tokenBalance") or "0"
        metadata = item.get("tokenMetadata") or {}
        decimals = metadata.get("decimals") or 18
        symbol = metadata.get("symbol") or ""

        # Convert hex or int balance string to human-readable float
        try:
            int_val = int(raw_balance, 16) if str(raw_balance).startswith("0x") else int(raw_balance)
            bal = int_val / (10 ** decimals)
        except ValueError:
            bal = 0.0

        # Calculate USD price if available
        prices = item.get("tokenPrices") or []
        usd_price = float(prices[0].get("value") or 0.0) if prices else 0.0
        usd_val = bal * usd_price

        if item.get("tokenAddress") is None:  # Native coin
            native_str = f"{bal:.4f} {symbol}".strip()
            native_usd = usd_val
        else:
            tokens_usd += usd_val

    total_usd = native_usd + tokens_usd

    return {
        "address": address,
        "network": SUPPORTED_CHAINS.get(chain_id, chain_id),
        "native_balance": native_str,
        "tokens_usd": tokens_usd,
        "total_usd": total_usd,
    }