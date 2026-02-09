"""
Vercel Serverless Function - Coinhacko Terminal API
Serves both the frontend HTML and API endpoints.
Uses in-memory TTL cache (persists across warm invocations).
"""

import json
import time
import random
import os
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ---------------------------------------------------------------------------
# We can't import requests in Vercel by default, so use urllib
# ---------------------------------------------------------------------------
from urllib.request import urlopen, Request
from urllib.error import URLError

HYPERLIQUID_API_URL = "https://api.hyperliquid.xyz/info"

# ---------------------------------------------------------------------------
# COIN_REF: symbol -> { name, circ_supply }
# ---------------------------------------------------------------------------
COIN_REF = {
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
    "SUSHI":  {"name": "SushiSwap",            "circ_supply": 278_000_000},
    "1INCH":  {"name": "1inch",                "circ_supply": 1_280_000_000},
    "YFI":    {"name": "yearn.finance",        "circ_supply": 33_000},
    "FET":    {"name": "Fetch.ai",             "circ_supply": 2_720_000_000},
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
    "GALA":   {"name": "Gala",                 "circ_supply": 42_300_000_000},
    "APE":    {"name": "ApeCoin",              "circ_supply": 604_000_000},
    "CHZ":    {"name": "Chiliz",               "circ_supply": 8_890_000_000},
    "BLUR":   {"name": "Blur",                 "circ_supply": 3_660_000_000},
    "CFX":    {"name": "Conflux",              "circ_supply": 5_600_000_000},
    "CELO":   {"name": "Celo",                 "circ_supply": 599_000_000},
    "KAS":    {"name": "Kaspa",                "circ_supply": 25_800_000_000},
    "MNT":    {"name": "Mantle",               "circ_supply": 3_290_000_000},
    "CAKE":   {"name": "PancakeSwap",          "circ_supply": 392_000_000},
    "ORDI":   {"name": "ORDI",                 "circ_supply": 21_000_000},
    "HBAR":   {"name": "Hedera",               "circ_supply": 38_100_000_000},
    "POL":    {"name": "Polygon",              "circ_supply": 10_000_000_000},
    "MOVE":   {"name": "Movement",             "circ_supply": 2_250_000_000},
    "TRUMP":  {"name": "Official Trump",       "circ_supply": 200_000_000},
    "FARTCOIN":{"name": "Fartcoin",            "circ_supply": 1_000_000_000},
    "VIRTUAL": {"name": "Virtuals Protocol",   "circ_supply": 1_000_000_000},
    # k-prefixed perps (1 unit = 1000 tokens)
    "kPEPE":  {"name": "Pepe",                 "circ_supply": 420_690_000_000},
    "kSHIB":  {"name": "Shiba Inu",            "circ_supply": 589_000_000_000},
    "kBONK":  {"name": "Bonk",                 "circ_supply": 76_800_000_000},
    "kFLOKI": {"name": "Floki",                "circ_supply": 9_700_000_000},
    "kLUNC":  {"name": "Terra Classic",        "circ_supply": 6_500_000_000},
    "kDOGS":  {"name": "Dogs",                 "circ_supply": 517_000_000},
    "kNEIRO": {"name": "Neiro",                "circ_supply": 1_000_000_000},
    # RWA / commodity
    "PAXG":   {"name": "PAX Gold",             "circ_supply": 244_500},
    # HIP-3 spot
    "PURR":   {"name": "Purr",                 "circ_supply": 596_000_000},
    "HFUN":   {"name": "HyperFun",             "circ_supply": 996_000},
}

BRIDGED_TOKEN_MAP = {"AAVE0": "AAVE", "AVAX0": "AVAX"}
SPOT_MIN_VOLUME = 500

# ---------------------------------------------------------------------------
# In-memory TTL cache (survives across warm invocations on Vercel)
# ---------------------------------------------------------------------------
_cache = {"data": [], "ts": 0}
CACHE_TTL = 15  # seconds


def _hl_post(payload):
    """POST to Hyperliquid info endpoint using stdlib urllib."""
    body = json.dumps(payload).encode()
    req = Request(HYPERLIQUID_API_URL, data=body,
                  headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def fetch_all_coins():
    """Fetch perp + spot data from Hyperliquid, merge, sort by mcap."""

    # Check cache
    if _cache["data"] and (time.time() - _cache["ts"]) < CACHE_TTL:
        return _cache["data"]

    combined = {}

    # --- Perps ---
    perp_resp = _hl_post({"type": "metaAndAssetCtxs"})
    for market, ctx in zip(perp_resp[0]["universe"], perp_resp[1]):
        symbol = market["name"]
        if market.get("isDelisted"):
            continue
        mid_px = float(ctx.get("midPx") or 0)
        prev_px = float(ctx.get("prevDayPx") or 0)
        day_vol = float(ctx.get("dayNtlVlm") or 0)
        oracle_px = float(ctx.get("oraclePx") or mid_px)
        pct = ((mid_px - prev_px) / prev_px * 100) if prev_px > 0 else 0
        ref = COIN_REF.get(symbol, {})
        circ = ref.get("circ_supply", 0)
        combined[symbol] = {
            "symbol": symbol, "name": ref.get("name", symbol),
            "price": mid_px, "price_change_24h": round(pct, 2),
            "market_cap": oracle_px * circ if circ else 0,
            "volume": day_vol, "type": "perp",
        }

    # --- Spot ---
    spot_resp = _hl_post({"type": "spotMetaAndAssetCtxs"})
    tokens = {t["index"]: t for t in spot_resp[0].get("tokens", [])}
    universe = spot_resp[0].get("universe", [])
    spot_candidates = {}

    for i, ctx in enumerate(spot_resp[1]):
        if i >= len(universe):
            break
        raw = tokens.get(universe[i]["tokens"][0], {}).get("name", "")
        sym = BRIDGED_TOKEN_MAP.get(raw, raw)
        if sym in combined or f"k{sym}" in combined:
            continue
        mid_px = float(ctx.get("midPx") or 0)
        if mid_px <= 0:
            continue
        prev_px = float(ctx.get("prevDayPx") or 0)
        day_vol = float(ctx.get("dayNtlVlm") or 0)
        ref = COIN_REF.get(sym) or COIN_REF.get(raw, {})
        if not (universe[i].get("isCanonical") or ref or day_vol >= SPOT_MIN_VOLUME):
            continue
        spot_candidates.setdefault(sym, []).append({
            "mid_px": mid_px, "prev_px": prev_px,
            "day_vol": day_vol, "ref": ref, "raw": raw,
        })

    for sym, cands in spot_candidates.items():
        best = max(cands, key=lambda c: c["day_vol"])
        mid_px = best["mid_px"]
        prev_px = best["prev_px"]
        ref = best["ref"]
        pct = ((mid_px - prev_px) / prev_px * 100) if prev_px > 0 else 0
        circ = ref.get("circ_supply", 0)
        combined[sym] = {
            "symbol": sym, "name": ref.get("name", sym),
            "price": mid_px, "price_change_24h": round(pct, 2),
            "market_cap": mid_px * circ if circ else 0,
            "volume": best["day_vol"], "type": "spot",
        }

    result = sorted(combined.values(),
                    key=lambda x: (x["market_cap"], x["volume"]), reverse=True)

    _cache["data"] = result
    _cache["ts"] = time.time()
    return result


def format_coins(coins):
    """Format coin list for the frontend JSON."""
    out = []
    for rank, item in enumerate(coins, 1):
        px = item["price"]
        if px <= 0:
            continue
        seed = hash(item["symbol"]) % 10000
        rng = random.Random(seed)
        spark = []
        cur = px * 0.97
        for _ in range(168):
            cur *= (1 + rng.uniform(-0.015, 0.015))
            spark.append(cur)
        spark[-1] = px
        sym_low = item["symbol"].lower()
        out.append({
            "id": sym_low, "symbol": item["symbol"], "name": item["name"],
            "image": f"https://raw.githubusercontent.com/spothq/cryptocurrency-icons/master/128/color/{sym_low}.png",
            "current_price": px, "market_cap_rank": rank,
            "price_change_percentage_24h": item["price_change_24h"],
            "market_cap": item["market_cap"],
            "total_volume": item["volume"],
            "high_24h": px * (1 + abs(item["price_change_24h"]) / 100),
            "low_24h": px * (1 - abs(item["price_change_24h"]) / 100),
            "circulating_supply": item["market_cap"] / px if px > 0 else 0,
            "type": item.get("type", "perp"),
            "sparkline_in_7d": {"price": spark},
        })
    return out


# ---------------------------------------------------------------------------
# Read the HTML template once at module level (cold start)
# ---------------------------------------------------------------------------
_html_template = None

def get_html():
    global _html_template
    if _html_template is None:
        # Try multiple paths (local dev vs Vercel)
        for path in ["templates/index.html", "api/../templates/index.html",
                      os.path.join(os.path.dirname(__file__), "..", "templates", "index.html")]:
            try:
                with open(path, "r") as f:
                    _html_template = f.read()
                    break
            except FileNotFoundError:
                continue
        if _html_template is None:
            _html_template = "<h1>Template not found</h1>"
    return _html_template


# ---------------------------------------------------------------------------
# Vercel handler
# ---------------------------------------------------------------------------
class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        qs = parse_qs(parsed.query)

        if path == "/api/coins":
            self._handle_coins(qs)
        elif path.startswith("/api/coin/"):
            coin_id = path.split("/api/coin/")[-1]
            self._handle_coin_detail(coin_id)
        elif path == "/api/status":
            self._handle_status()
        else:
            # Serve HTML
            self._respond(200, get_html(), content_type="text/html")

    def _handle_coins(self, qs):
        all_coins = format_coins(fetch_all_coins())
        page = int(qs.get("page", [1])[0])
        per_page = min(int(qs.get("per_page", [100])[0]), 500)
        start = (page - 1) * per_page
        self._json_response({
            "data": all_coins[start:start + per_page],
            "page": page, "per_page": per_page,
            "total": len(all_coins),
            "total_pages": (len(all_coins) + per_page - 1) // per_page,
        })

    def _handle_coin_detail(self, coin_id):
        all_coins = format_coins(fetch_all_coins())
        coin = next((c for c in all_coins if c["id"] == coin_id.lower()), None)
        if coin:
            self._json_response(coin)
        else:
            self._json_response({"error": "Coin not found"}, status=404)

    def _handle_status(self):
        self._json_response({
            "status": "online", "source": "Hyperliquid DEX",
            "cache_age": time.time() - _cache["ts"] if _cache["ts"] else None,
            "cached_coins": len(_cache["data"]),
        })

    def _json_response(self, data, status=200):
        self._respond(status, json.dumps(data), content_type="application/json")

    def _respond(self, status, body, content_type="text/plain"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body.encode() if isinstance(body, str) else body)
