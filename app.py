"""
Coinhacko Terminal - Full Stack Web Application
Real-time cryptocurrency data from Hyperliquid DEX (perps + HIP-3 spot)
"""

import json
import requests
from flask import Flask, render_template, jsonify, request as flask_request
from flask_cors import CORS
from datetime import datetime
import time
import threading
import random

app = Flask(__name__)
CORS(app)

HYPERLIQUID_API_URL = "https://api.hyperliquid.xyz/info"

# ---------------------------------------------------------------------------
# Reference data: symbol -> { full_name, circulating_supply }
# circulating_supply is used to compute market_cap = price * circ_supply
# Sources: CoinGecko / CoinMarketCap snapshot.  Update periodically.
# ---------------------------------------------------------------------------
COIN_REF = {
    # --- mega caps ---
    "BTC":    {"name": "Bitcoin",              "circ_supply": 19_820_000},
    "ETH":    {"name": "Ethereum",             "circ_supply": 120_500_000},
    "BNB":    {"name": "BNB",                  "circ_supply": 140_890_000},
    "SOL":    {"name": "Solana",               "circ_supply": 517_000_000},
    "XRP":    {"name": "XRP",                  "circ_supply": 57_800_000_000},
    "DOGE":   {"name": "Dogecoin",             "circ_supply": 148_000_000_000},
    "ADA":    {"name": "Cardano",              "circ_supply": 37_600_000_000},
    "TRX":    {"name": "TRON",                 "circ_supply": 84_200_000_000},
    "AVAX":   {"name": "Avalanche",            "circ_supply": 414_000_000},
    "LINK":   {"name": "Chainlink",            "circ_supply": 657_000_000},
    "TON":    {"name": "Toncoin",              "circ_supply": 5_120_000_000},
    "DOT":    {"name": "Polkadot",             "circ_supply": 1_550_000_000},
    "MATIC":  {"name": "Polygon",              "circ_supply": 10_000_000_000},
    "LTC":    {"name": "Litecoin",             "circ_supply": 75_400_000},
    "BCH":    {"name": "Bitcoin Cash",         "circ_supply": 19_800_000},
    "ICP":    {"name": "Internet Computer",    "circ_supply": 527_000_000},
    "UNI":    {"name": "Uniswap",              "circ_supply": 600_500_000},
    "ETC":    {"name": "Ethereum Classic",     "circ_supply": 149_000_000},
    "APT":    {"name": "Aptos",                "circ_supply": 522_000_000},
    "NEAR":   {"name": "NEAR Protocol",        "circ_supply": 1_240_000_000},
    "FIL":    {"name": "Filecoin",             "circ_supply": 620_000_000},
    "ATOM":   {"name": "Cosmos",               "circ_supply": 398_000_000},
    "XLM":    {"name": "Stellar",              "circ_supply": 30_600_000_000},
    "STX":    {"name": "Stacks",               "circ_supply": 1_520_000_000},
    "ARB":    {"name": "Arbitrum",             "circ_supply": 4_250_000_000},
    "OP":     {"name": "Optimism",             "circ_supply": 1_640_000_000},
    "SUI":    {"name": "Sui",                  "circ_supply": 3_250_000_000},
    "SEI":    {"name": "Sei",                  "circ_supply": 5_100_000_000},
    "INJ":    {"name": "Injective",            "circ_supply": 98_100_000},
    "MKR":    {"name": "Maker",                "circ_supply": 881_000},
    "AAVE":   {"name": "Aave",                 "circ_supply": 15_100_000},
    "RENDER": {"name": "Render",               "circ_supply": 517_000_000},
    "GRT":    {"name": "The Graph",            "circ_supply": 10_300_000_000},
    "IMX":    {"name": "Immutable X",          "circ_supply": 1_690_000_000},
    "FTM":    {"name": "Fantom",               "circ_supply": 2_800_000_000},
    "ALGO":   {"name": "Algorand",             "circ_supply": 8_500_000_000},
    "VET":    {"name": "VeChain",              "circ_supply": 86_700_000_000},
    "CRV":    {"name": "Curve DAO",            "circ_supply": 1_280_000_000},
    "SAND":   {"name": "The Sandbox",          "circ_supply": 2_390_000_000},
    "MANA":   {"name": "Decentraland",         "circ_supply": 1_890_000_000},
    "AXS":    {"name": "Axie Infinity",        "circ_supply": 152_000_000},
    "SNX":    {"name": "Synthetix",            "circ_supply": 335_000_000},
    "LDO":    {"name": "Lido DAO",             "circ_supply": 894_000_000},
    "DYDX":   {"name": "dYdX",                 "circ_supply": 730_000_000},
    "ENS":    {"name": "Ethereum Name Service","circ_supply": 37_600_000},
    "COMP":   {"name": "Compound",             "circ_supply": 10_000_000},
    "RPL":    {"name": "Rocket Pool",          "circ_supply": 20_500_000},
    "BAL":    {"name": "Balancer",             "circ_supply": 67_000_000},
    "SUSHI":  {"name": "SushiSwap",            "circ_supply": 278_000_000},
    "1INCH":  {"name": "1inch",                "circ_supply": 1_280_000_000},
    "YFI":    {"name": "yearn.finance",        "circ_supply": 33_000},
    "ZRX":    {"name": "0x",                   "circ_supply": 850_000_000},
    "KNC":    {"name": "Kyber Network",        "circ_supply": 172_000_000},
    "UMA":    {"name": "UMA",                  "circ_supply": 82_000_000},
    "FET":    {"name": "Fetch.ai",             "circ_supply": 2_720_000_000},
    "RNDR":   {"name": "Render",               "circ_supply": 517_000_000},
    "WLD":    {"name": "Worldcoin",            "circ_supply": 540_000_000},
    "JTO":    {"name": "Jito",                 "circ_supply": 329_000_000},
    "JUP":    {"name": "Jupiter",              "circ_supply": 1_350_000_000},
    "TIA":    {"name": "Celestia",             "circ_supply": 416_000_000},
    "PYTH":   {"name": "Pyth Network",         "circ_supply": 3_600_000_000},
    "W":      {"name": "Wormhole",             "circ_supply": 1_800_000_000},
    "STRK":   {"name": "Starknet",             "circ_supply": 1_810_000_000},
    "WIF":    {"name": "dogwifhat",            "circ_supply": 998_900_000},
    "BONK":   {"name": "Bonk",                 "circ_supply": 76_800_000_000_000},
    "PEPE":   {"name": "Pepe",                 "circ_supply": 420_690_000_000_000},
    "FLOKI":  {"name": "Floki",                "circ_supply": 9_700_000_000_000},
    "SHIB":   {"name": "Shiba Inu",            "circ_supply": 589_000_000_000_000},
    "HYPE":   {"name": "Hyperliquid",          "circ_supply": 333_900_000},
    "ENA":    {"name": "Ethena",               "circ_supply": 5_690_000_000},
    "PENDLE": {"name": "Pendle",               "circ_supply": 286_000_000},
    "ONDO":   {"name": "Ondo Finance",         "circ_supply": 3_290_000_000},
    "TAO":    {"name": "Bittensor",            "circ_supply": 7_770_000},
    "FLR":    {"name": "Flare",                "circ_supply": 34_600_000_000},
    "RUNE":   {"name": "THORChain",            "circ_supply": 342_000_000},
    "THETA":  {"name": "Theta Network",        "circ_supply": 1_000_000_000},
    "EGLD":   {"name": "MultiversX",           "circ_supply": 27_800_000},
    "FLOW":   {"name": "Flow",                 "circ_supply": 1_560_000_000},
    "NEO":    {"name": "Neo",                  "circ_supply": 70_500_000},
    "GALA":   {"name": "Gala",                 "circ_supply": 42_300_000_000},
    "APE":    {"name": "ApeCoin",              "circ_supply": 604_000_000},
    "CHZ":    {"name": "Chiliz",               "circ_supply": 8_890_000_000},
    "BLUR":   {"name": "Blur",                 "circ_supply": 3_660_000_000},
    "CFX":    {"name": "Conflux",              "circ_supply": 5_600_000_000},
    "CELO":   {"name": "Celo",                 "circ_supply": 599_000_000},
    "MEME":   {"name": "Memecoin",             "circ_supply": 25_000_000_000},
    "LOOM":   {"name": "Loom Network",         "circ_supply": 1_300_000_000},
    "COTI":   {"name": "COTI",                 "circ_supply": 1_600_000_000},
    "STORJ":  {"name": "Storj",                "circ_supply": 437_000_000},
    "ANKR":   {"name": "Ankr",                 "circ_supply": 10_000_000_000},
    "CELR":   {"name": "Celer Network",        "circ_supply": 7_890_000_000},
    "ZK":     {"name": "zkSync",               "circ_supply": 3_680_000_000},
    "MASK":   {"name": "Mask Network",         "circ_supply": 100_000_000},
    "ENJ":    {"name": "Enjin Coin",           "circ_supply": 1_000_000_000},
    "SKL":    {"name": "SKALE",                "circ_supply": 5_700_000_000},
    "BAND":   {"name": "Band Protocol",        "circ_supply": 153_000_000},
    "PERP":   {"name": "Perpetual Protocol",   "circ_supply": 151_000_000},
    "RSR":    {"name": "Reserve Rights",       "circ_supply": 53_000_000_000},
    "ZIL":    {"name": "Zilliqa",              "circ_supply": 19_400_000_000},
    "RVN":    {"name": "Ravencoin",            "circ_supply": 14_500_000_000},
    "GMT":    {"name": "STEPN",                "circ_supply": 2_950_000_000},
    "HNT":    {"name": "Helium",               "circ_supply": 161_000_000},
    "SPELL":  {"name": "Spell Token",          "circ_supply": 139_000_000_000_000},
    "KAS":    {"name": "Kaspa",                "circ_supply": 25_800_000_000},
    "MNT":    {"name": "Mantle",               "circ_supply": 3_290_000_000},
    "CAKE":   {"name": "PancakeSwap",          "circ_supply": 392_000_000},
    "ORDI":   {"name": "ORDI",                 "circ_supply": 21_000_000},
    "RAY":    {"name": "Raydium",              "circ_supply": 358_000_000},
    "IOTX":   {"name": "IoTeX",                "circ_supply": 9_540_000_000},
    "OCEAN":  {"name": "Ocean Protocol",       "circ_supply": 613_000_000},
    "IOTA":   {"name": "IOTA",                 "circ_supply": 3_560_000_000},
    "HBAR":   {"name": "Hedera",               "circ_supply": 38_100_000_000},
    "POL":    {"name": "Polygon",              "circ_supply": 10_000_000_000},
    "MOVE":   {"name": "Movement",             "circ_supply": 2_250_000_000},
    "TRUMP":  {"name": "Official Trump",       "circ_supply": 200_000_000},
    "AI16Z":  {"name": "ai16z",                "circ_supply": 1_100_000_000},
    "FARTCOIN":{"name": "Fartcoin",            "circ_supply": 1_000_000_000},
    "VIRTUAL": {"name": "Virtuals Protocol",   "circ_supply": 1_000_000_000},
    "POPCAT":  {"name": "Popcat",              "circ_supply": 980_000_000},
    "MEW":     {"name": "cat in a dogs world", "circ_supply": 88_000_000_000},
    "MOTHER":  {"name": "Mother Iggy",         "circ_supply": 999_000_000},
    # --- k-prefixed perps (1 unit = 1000 tokens, so circ = real_supply / 1000) ---
    "kPEPE":  {"name": "Pepe",                 "circ_supply": 420_690_000_000},   # 420.69T / 1000
    "kSHIB":  {"name": "Shiba Inu",            "circ_supply": 589_000_000_000},   # 589T / 1000
    "kBONK":  {"name": "Bonk",                 "circ_supply": 76_800_000_000},    # 76.8T / 1000
    "kFLOKI": {"name": "Floki",                "circ_supply": 9_700_000_000},     # 9.7T / 1000
    "kLUNC":  {"name": "Terra Classic",        "circ_supply": 6_500_000_000},     # 6.5T / 1000
    "kDOGS":  {"name": "Dogs",                 "circ_supply": 517_000_000},       # 517B / 1000
    "kNEIRO": {"name": "Neiro",                "circ_supply": 1_000_000_000},     # 1T / 1000
    # --- RWA / commodity perps ---
    "PAXG":   {"name": "PAX Gold",             "circ_supply": 244_500},
    "XAUT":   {"name": "Tether Gold",          "circ_supply": 246_500},
    # --- HIP-3 spot-only tokens ---
    "PURR":   {"name": "Purr",                 "circ_supply": 596_000_000},
    "HFUN":   {"name": "HyperFun",             "circ_supply": 996_000},
}

# Map Hyperliquid's 0-suffixed bridged token names to canonical symbols.
# e.g. XAUT0 on HL spot -> "XAUT" in COIN_REF
# Map Hyperliquid's 0-suffixed bridged token names to canonical symbols.
# NOTE: Only map tokens whose spot price is reliable.
# XAUT0 spot data is unreliable; use PAXG perp for gold exposure.
BRIDGED_TOKEN_MAP = {
    "AAVE0": "AAVE",
    "AVAX0": "AVAX",
}

# Minimum 24h volume (USD) for a spot asset to be included even without COIN_REF
SPOT_MIN_VOLUME = 500

# ---------------------------------------------------------------------------
# Caches
# ---------------------------------------------------------------------------
price_cache = []
cache_timestamp = 0
CACHE_DURATION = 10  # seconds


def _hl_post(payload):
    """POST helper for Hyperliquid info endpoint."""
    r = requests.post(HYPERLIQUID_API_URL, json=payload,
                      headers={"Content-Type": "application/json"}, timeout=10)
    r.raise_for_status()
    return r.json()


def fetch_hyperliquid_data():
    """Fetch perp + spot data from Hyperliquid and combine into a unified list."""
    try:
        # ------ Perp data (metaAndAssetCtxs) ------
        perp_resp = _hl_post({"type": "metaAndAssetCtxs"})
        perp_meta = perp_resp[0]
        perp_ctxs = perp_resp[1]

        combined = {}  # symbol -> dict

        for market, ctx in zip(perp_meta["universe"], perp_ctxs):
            symbol = market["name"]
            if market.get("isDelisted"):
                continue

            mid_px = float(ctx.get("midPx") or 0)
            prev_px = float(ctx.get("prevDayPx") or 0)
            day_vol = float(ctx.get("dayNtlVlm") or 0)
            oracle_px = float(ctx.get("oraclePx") or mid_px)

            pct_24h = ((mid_px - prev_px) / prev_px * 100) if prev_px > 0 else 0

            ref = COIN_REF.get(symbol, {})
            circ = ref.get("circ_supply", 0)
            market_cap = oracle_px * circ if circ else 0

            combined[symbol] = {
                "symbol": symbol,
                "name": ref.get("name", symbol),
                "price": mid_px,
                "price_change_24h": round(pct_24h, 2),
                "market_cap": market_cap,
                "volume": day_vol,
                "high_24h": mid_px * 1.0,   # placeholder; updated below
                "low_24h": mid_px * 1.0,
                "type": "perp",
                "max_leverage": market.get("maxLeverage"),
            }

        # ------ Spot data (spotMetaAndAssetCtxs) ------
        spot_resp = _hl_post({"type": "spotMetaAndAssetCtxs"})
        spot_meta = spot_resp[0]
        spot_ctxs = spot_resp[1]
        tokens = spot_meta.get("tokens", [])
        universe = spot_meta.get("universe", [])
        token_map = {t["index"]: t for t in tokens}

        # Collect ALL candidates per base token, then pick the best pair
        # (highest 24h volume) for each.
        spot_candidates = {}  # display_symbol -> list of candidate dicts

        for i, ctx in enumerate(spot_ctxs):
            if i >= len(universe):
                break

            u = universe[i]
            base_idx = u["tokens"][0]
            base_token = token_map.get(base_idx, {})
            raw_name = base_token.get("name", "")

            # Resolve bridged token names (XAUT0 -> XAUT, BNB0 -> BNB, etc.)
            display_symbol = BRIDGED_TOKEN_MAP.get(raw_name, raw_name)

            # Skip if perp already covers this
            if display_symbol in combined or f"k{display_symbol}" in combined:
                continue

            mid_px = float(ctx.get("midPx") or 0)
            prev_px = float(ctx.get("prevDayPx") or 0)
            day_vol = float(ctx.get("dayNtlVlm") or 0)

            if mid_px <= 0:
                continue

            ref = COIN_REF.get(display_symbol) or COIN_REF.get(raw_name, {})
            is_canonical = u.get("isCanonical", False)
            in_ref = bool(ref)
            has_volume = day_vol >= SPOT_MIN_VOLUME

            if not (is_canonical or in_ref or has_volume):
                continue

            spot_candidates.setdefault(display_symbol, []).append({
                "raw_name": raw_name,
                "mid_px": mid_px,
                "prev_px": prev_px,
                "day_vol": day_vol,
                "ref": ref,
                "is_canonical": is_canonical,
            })

        # Pick best pair per token (highest volume)
        for display_symbol, candidates in spot_candidates.items():
            best = max(candidates, key=lambda c: c["day_vol"])

            mid_px = best["mid_px"]
            prev_px = best["prev_px"]
            ref = best["ref"]
            pct_24h = ((mid_px - prev_px) / prev_px * 100) if prev_px > 0 else 0
            circ = ref.get("circ_supply", 0)
            market_cap = mid_px * circ if circ else 0

            combined[display_symbol] = {
                "symbol": display_symbol,
                "name": ref.get("name", display_symbol),
                "price": mid_px,
                "price_change_24h": round(pct_24h, 2),
                "market_cap": market_cap,
                "volume": best["day_vol"],
                "high_24h": mid_px,
                "low_24h": mid_px,
                "type": "spot",
            }

        # Convert to sorted list: highest market_cap first,
        # then assets without market cap sorted by volume
        result = list(combined.values())
        result.sort(key=lambda x: (x["market_cap"], x["volume"]), reverse=True)

        return result

    except Exception as e:
        print(f"Error fetching Hyperliquid data: {e}")
        import traceback; traceback.print_exc()
        return []


def update_cache():
    """Refresh the global cache."""
    global price_cache, cache_timestamp
    data = fetch_hyperliquid_data()
    if data:
        price_cache = data
        cache_timestamp = time.time()
        print(f"[{datetime.now():%H:%M:%S}] Cache updated: {len(data)} assets")


def get_formatted_coins():
    """Return the coin list formatted for the frontend."""
    global price_cache, cache_timestamp

    if time.time() - cache_timestamp > CACHE_DURATION:
        update_cache()

    data = price_cache if price_cache else []

    formatted = []
    for rank, item in enumerate(data, start=1):
        base_price = item["price"]
        if base_price <= 0:
            continue

        # Deterministic-ish sparkline based on symbol hash so it doesn't
        # re-randomise on every request
        seed = hash(item["symbol"]) % 10000
        rng = random.Random(seed)
        sparkline = []
        cur = base_price * 0.97
        for _ in range(168):
            cur *= (1 + rng.uniform(-0.015, 0.015))
            sparkline.append(cur)
        sparkline[-1] = base_price

        sym_lower = item["symbol"].lower()

        formatted.append({
            "id": sym_lower,
            "symbol": item["symbol"],
            "name": item["name"],
            "image": f"https://raw.githubusercontent.com/spothq/cryptocurrency-icons/master/128/color/{sym_lower}.png",
            "current_price": base_price,
            "market_cap_rank": rank,
            "price_change_percentage_24h": item["price_change_24h"],
            "market_cap": item["market_cap"],
            "total_volume": item["volume"],
            "high_24h": base_price * (1 + abs(item["price_change_24h"]) / 100),
            "low_24h": base_price * (1 - abs(item["price_change_24h"]) / 100),
            "circulating_supply": item["market_cap"] / base_price if base_price > 0 else 0,
            "type": item.get("type", "perp"),
            "sparkline_in_7d": {"price": sparkline},
        })

    return formatted


def background_updater():
    while True:
        time.sleep(CACHE_DURATION)
        update_cache()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/coins")
def get_coins():
    all_coins = get_formatted_coins()
    page = flask_request.args.get("page", 1, type=int)
    per_page = flask_request.args.get("per_page", 100, type=int)
    per_page = min(per_page, 500)  # cap

    start = (page - 1) * per_page
    end = start + per_page
    page_data = all_coins[start:end]

    return jsonify({
        "data": page_data,
        "page": page,
        "per_page": per_page,
        "total": len(all_coins),
        "total_pages": (len(all_coins) + per_page - 1) // per_page,
    })


@app.route("/api/coin/<coin_id>")
def get_coin_detail(coin_id):
    coins = get_formatted_coins()
    coin = next((c for c in coins if c["id"] == coin_id.lower()), None)
    if coin:
        return jsonify(coin)
    return jsonify({"error": "Coin not found"}), 404


# ---------------------------------------------------------------------------
# Liquidation Level Estimator
# ---------------------------------------------------------------------------
LIQUIDATION_THRESHOLD = 50_000_000  # $50M "pain" threshold
MAINT_MARGIN = 0.005  # ~0.5% maintenance margin on Hyperliquid

# Assumed distribution of OI across leverage tiers (heuristic)
BASE_LEVERAGE_DIST = {
    2: 0.10, 3: 0.12, 5: 0.18, 10: 0.25,
    15: 0.15, 20: 0.10, 25: 0.05, 40: 0.05,
}

liq_cache = {"data": None, "ts": 0}
LIQ_CACHE_TTL = 30  # seconds


def estimate_liquidations(symbols=("BTC", "ETH", "SOL")):
    """Estimate liquidation levels for given perp symbols."""

    # Check cache
    if liq_cache["data"] and (time.time() - liq_cache["ts"]) < LIQ_CACHE_TTL:
        return liq_cache["data"]

    perp_resp = _hl_post({"type": "metaAndAssetCtxs"})
    perp_meta = perp_resp[0]["universe"]
    perp_ctxs = perp_resp[1]

    results = []

    for market, ctx in zip(perp_meta, perp_ctxs):
        symbol = market["name"]
        if symbol not in symbols:
            continue

        max_lev = market["maxLeverage"]
        oi_coins = float(ctx.get("openInterest") or 0)
        oracle = float(ctx.get("oraclePx") or 0)
        funding = float(ctx.get("funding") or 0)
        mid_px = float(ctx.get("midPx") or oracle)

        if oracle <= 0 or oi_coins <= 0:
            continue

        oi_usd = oi_coins * oracle
        net_direction = "LONG" if funding >= 0 else "SHORT"

        # Build leverage distribution capped at this market's max leverage
        lev_dist = {k: v for k, v in BASE_LEVERAGE_DIST.items() if k <= max_lev}
        total_w = sum(lev_dist.values())
        lev_dist = {k: v / total_w for k, v in lev_dist.items()}

        # Majority side = net direction, minority side gets ~30% of OI
        majority_pct = 0.70
        minority_pct = 0.30

        levels = []

        for leverage, pct_of_oi in sorted(lev_dist.items()):
            liq_distance = (1 / leverage) * (1 - MAINT_MARGIN)
            distance_pct = liq_distance * 100

            # Only include levels within 10% of current price
            if distance_pct > 10:
                continue

            # Longs get liquidated when price drops
            long_liq_price = oracle * (1 - liq_distance)
            long_amount = oi_usd * pct_of_oi * majority_pct if net_direction == "LONG" else oi_usd * pct_of_oi * minority_pct

            levels.append({
                "side": "LONG",
                "leverage": leverage,
                "liq_price": round(long_liq_price, 2),
                "distance_pct": round(distance_pct, 2),
                "amount_at_risk": round(long_amount),
                "direction": "below",  # price needs to go below
            })

            # Shorts get liquidated when price rises
            short_liq_price = oracle * (1 + liq_distance)
            short_amount = oi_usd * pct_of_oi * minority_pct if net_direction == "LONG" else oi_usd * pct_of_oi * majority_pct

            levels.append({
                "side": "SHORT",
                "leverage": leverage,
                "liq_price": round(short_liq_price, 2),
                "distance_pct": round(distance_pct, 2),
                "amount_at_risk": round(short_amount),
                "direction": "above",  # price needs to go above
            })

        # Sort levels by distance (nearest first)
        levels.sort(key=lambda x: x["distance_pct"])

        # Find the "next big liquidation" - nearest level >= threshold
        next_big_below = None
        next_big_above = None
        for lv in levels:
            if lv["amount_at_risk"] >= LIQUIDATION_THRESHOLD:
                if lv["direction"] == "below" and not next_big_below:
                    next_big_below = lv
                elif lv["direction"] == "above" and not next_big_above:
                    next_big_above = lv

        results.append({
            "symbol": symbol,
            "price": mid_px,
            "oracle_price": oracle,
            "open_interest_usd": round(oi_usd),
            "funding_rate": funding,
            "net_direction": net_direction,
            "max_leverage": max_lev,
            "levels": levels,
            "next_big_liq_below": next_big_below,
            "next_big_liq_above": next_big_above,
            "threshold": LIQUIDATION_THRESHOLD,
        })

    liq_cache["data"] = results
    liq_cache["ts"] = time.time()
    return results


@app.route("/api/liquidations")
def get_liquidations():
    """Get liquidation level estimates for major assets."""
    symbols = flask_request.args.get("symbols", "BTC,ETH,SOL")
    symbol_list = tuple(s.strip().upper() for s in symbols.split(","))
    return jsonify(estimate_liquidations(symbol_list))


@app.route("/api/status")
def get_status():
    return jsonify({
        "status": "online",
        "source": "Hyperliquid DEX",
        "cache_age": time.time() - cache_timestamp if cache_timestamp > 0 else None,
        "cached_coins": len(price_cache),
        "last_update": datetime.fromtimestamp(cache_timestamp).isoformat() if cache_timestamp > 0 else None,
    })


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Initializing Hyperliquid data cache...")
    update_cache()

    updater_thread = threading.Thread(target=background_updater, daemon=True)
    updater_thread.start()

    print("\n" + "=" * 60)
    print("COINHACKO TERMINAL")
    print("=" * 60)
    print(f"\nServer running at: http://localhost:5555")
    print(f"Total assets loaded: {len(price_cache)}")
    print("\nAPI Endpoints:")
    print("  GET /api/coins        - All coins (sorted by market cap)")
    print("  GET /api/coin/<id>    - Single coin detail")
    print("  GET /api/status       - Server status")
    print("\nData: Hyperliquid perps + HIP-3 spot | Refresh: 10s")
    print("=" * 60 + "\n")

    app.run(debug=True, port=5555, host="0.0.0.0")
