"""Configuration module for the pDAI trading stack on PulseChain."""
import os
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuration settings for pDAI trading workflows."""

    # --- Blockchain / RPC -------------------------------------------------
    RPC_URL = os.getenv("RPC_URL", "https://rpc.pulsechain.com")
    _RPC_URLS_DEFAULT = [
        "https://rpc.pulsechain.com",
        "https://rpc-pulsechain.g4mm4.io",
        "https://rpc.pulsechainrpc.com",
        "https://pulsechain-rpc.publicnode.com",
    ]
    _ENV_RPC_URLS = os.getenv("RPC_URLS", "").strip()
    RPC_URLS = [u.strip() for u in _ENV_RPC_URLS.split(',') if u.strip()] or _RPC_URLS_DEFAULT
    CHAIN_ID = int(os.getenv("CHAIN_ID", "369"))

    # --- Token / contract addresses --------------------------------------
    PDAI_ADDRESS = os.getenv("PDAI_ADDRESS", "0x6B175474E89094C44Da98b954EedeAC495271d0F")
    DAI_ADDRESS = os.getenv("DAI_ADDRESS", "0xefD766cCb38EaF1dfd701853BFCe31359239F305")
    WPLS_ADDRESS = os.getenv("WPLS_ADDRESS", "0xA1077a294dDE1B09bB078844df40758a5D0f9a27")

    PDAI_WPLS_POOL = os.getenv("PDAI_WPLS_POOL", "0xaE8429918FdBF9a5867e3243697637Dc56aa76A1")
    DAI_WPLS_POOL = os.getenv("DAI_WPLS_POOL", "0xE56043671df55dE5CDf8459710433C10324DE0aE")

    PULSEX_ROUTER_V2 = os.getenv("PULSEX_ROUTER_V2", "0x165C3410fC91EF562C50559f7d2289fEbed552d9")

    # --- Wallet / trading defaults ---------------------------------------
    PRIVATE_KEY = os.getenv("PRIVATE_KEY", "")
    WALLET_ADDRESS = os.getenv("WALLET_ADDRESS", "")

    DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
    INITIAL_BALANCE = Decimal(os.getenv("INITIAL_BALANCE", "1000"))
    SLIPPAGE_TOLERANCE = Decimal(os.getenv("SLIPPAGE_TOLERANCE", "0.05"))
    MAX_TRADE_AMOUNT_PCT = Decimal(os.getenv("MAX_TRADE_AMOUNT_PCT", "0.1"))

    MA_SHORT_PERIOD = int(os.getenv("MA_SHORT_PERIOD", "10"))
    MA_LONG_PERIOD = int(os.getenv("MA_LONG_PERIOD", "30"))

    DATA_FETCH_INTERVAL = int(os.getenv("DATA_FETCH_INTERVAL", "60"))
    BACKTEST_DAYS = int(os.getenv("BACKTEST_DAYS", "365"))

    DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
    HTML_DIR = Path(os.getenv("HTML_DIR", "html_reports"))

    OHLCV_RANGE = os.getenv("OHLCV_RANGE", "30d").lower()
    _OHLCV_FILE_MAP = {
        '30d': 'pdai_ohlcv_dai_30day_5m.csv',
        '90d': 'pdai_ohlcv_dai_90day_5m.csv',
        '1y': 'pdai_ohlcv_dai_365day_5m.csv',
        '365d': 'pdai_ohlcv_dai_365day_5m.csv',
        '2y': 'pdai_ohlcv_730day_5m.csv',
    }

    @classmethod
    def ohlcv_candidates(cls) -> list[str]:
        pref = cls.OHLCV_RANGE if cls.OHLCV_RANGE in cls._OHLCV_FILE_MAP else '30d'
        order = {
            '30d': ['30d', '90d', '1y'],
            '90d': ['90d', '30d', '1y'],
            '1y': ['1y', '90d', '30d'],
            '365d': ['1y', '90d', '30d'],
            '2y': ['2y', '1y', '90d'],
        }
        seq = order.get(pref, ['30d', '90d', '1y'])
        return [str(cls.DATA_DIR / cls._OHLCV_FILE_MAP[k]) for k in seq]

    @classmethod
    def resolve_ohlcv_path(cls) -> str:
        for candidate in cls.ohlcv_candidates():
            if os.path.exists(candidate):
                return candidate
        return ""

    @classmethod
    def validate(cls) -> bool:
        if not cls.DEMO_MODE and (not cls.PRIVATE_KEY or not cls.WALLET_ADDRESS):
            raise ValueError("PRIVATE_KEY and WALLET_ADDRESS must be set for live trading")
        if cls.MA_SHORT_PERIOD >= cls.MA_LONG_PERIOD:
            raise ValueError("MA_SHORT_PERIOD must be less than MA_LONG_PERIOD")
        return True


TOKENS = {
    "pDAI": {
        "address": Config.PDAI_ADDRESS,
        "decimals": 18,
        "symbol": "pDAI",
    },
    "WPLS": {
        "address": Config.WPLS_ADDRESS,
        "decimals": 18,
        "symbol": "WPLS",
    },
    "DAI": {
        "address": Config.DAI_ADDRESS,
        "decimals": 18,
        "symbol": "DAI",
    },
}

# PulseX Router V2 ABI (minimal for swaps)
PULSEX_ROUTER_ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "name": "swapExactETHForTokens",
        "outputs": [
            {"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}
        ],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "name": "swapExactTokensForETH",
        "outputs": [
            {"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountOut", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"}
        ],
        "name": "getAmountsIn",
        "outputs": [
            {"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"}
        ],
        "name": "getAmountsOut",
        "outputs": [
            {"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

# ERC-20 Token ABI (minimal)
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [
            {"name": "_owner", "type": "address"},
            {"name": "_spender", "type": "address"}
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function"
    }
]
