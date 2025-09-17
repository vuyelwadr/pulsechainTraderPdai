"""Configuration module for the pDAI trading stack on PulseChain."""
from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv

# Load environment variables once on import so CLI entrypoints pick them up automatically.
load_dotenv()


@dataclass(frozen=True)
class Token:
    """Simple container for token metadata."""

    symbol: str
    address: str
    decimals: int


class Settings:
    """Centralised configuration for the pDAI trading toolkit."""

    # --- Blockchain / RPC -------------------------------------------------
    RPC_URL: str = os.getenv("RPC_URL", "https://rpc.pulsechain.com")
    _RPC_URLS_DEFAULT: List[str] = [
        "https://rpc.pulsechain.com",
        "https://rpc-pulsechain.g4mm4.io",
        "https://rpc.pulsechainrpc.com",
        "https://pulsechain-rpc.publicnode.com",
    ]
    RPC_URLS: List[str] = [u.strip() for u in os.getenv("RPC_URLS", "").split(",") if u.strip()] or _RPC_URLS_DEFAULT
    CHAIN_ID: int = int(os.getenv("CHAIN_ID", "369"))

    # --- Token addresses --------------------------------------------------
    PDAI_ADDRESS: str = os.getenv("PDAI_ADDRESS", "0x6B175474E89094C44Da98b954EedeAC495271d0F")
    DAI_ADDRESS: str = os.getenv("DAI_ADDRESS", "0xefD766cCb38EaF1dfd701853BFCe31359239F305")
    WPLS_ADDRESS: str = os.getenv("WPLS_ADDRESS", "0xA1077a294dDE1B09bB078844df40758a5D0f9a27")

    # Liquidity pool addresses used for price routing (pDAI -> WPLS -> DAI)
    PDAI_WPLS_POOL: str = os.getenv("PDAI_WPLS_POOL", "0xaE8429918FdBF9a5867e3243697637Dc56aa76A1")
    DAI_WPLS_POOL: str = os.getenv("DAI_WPLS_POOL", "0xE56043671df55dE5CDf8459710433C10324DE0aE")

    # PulseX router (v2) for on-chain quoting
    PULSEX_ROUTER_V2: str = os.getenv("PULSEX_ROUTER_V2", "0x165C3410fC91EF562C50559f7d2289fEbed552d9")

    # --- Trading defaults -------------------------------------------------
    DEMO_MODE: bool = os.getenv("DEMO_MODE", "true").lower() == "true"
    INITIAL_BALANCE: Decimal = Decimal(os.getenv("INITIAL_BALANCE", "1000"))
    MAX_TRADE_AMOUNT_PCT: Decimal = Decimal(os.getenv("MAX_TRADE_AMOUNT_PCT", "0.1"))
    SLIPPAGE_TOLERANCE: Decimal = Decimal(os.getenv("SLIPPAGE_TOLERANCE", "0.05"))

    # --- Strategy defaults ------------------------------------------------
    MA_SHORT_PERIOD: int = int(os.getenv("MA_SHORT_PERIOD", "10"))
    MA_LONG_PERIOD: int = int(os.getenv("MA_LONG_PERIOD", "30"))

    # --- Data / backtest defaults ----------------------------------------
    DATA_FETCH_INTERVAL: int = int(os.getenv("DATA_FETCH_INTERVAL", "60"))
    BACKTEST_DAYS: int = int(os.getenv("BACKTEST_DAYS", "30"))
    DATA_DIR: Path = Path(os.getenv("DATA_DIR", "data"))
    CACHE_DIR: Path = DATA_DIR / ".cache"
    HTML_DIR: Path = Path(os.getenv("HTML_DIR", "html_reports"))

    # Default OHLCV dataset preference order
    OHLCV_PREFERENCE: List[str] = [
        os.getenv("OHLCV_CSV", "pdai_ohlcv_dai_30day_5m.csv"),
        "pdai_ohlcv_dai_90day_5m.csv",
        "pdai_ohlcv_dai_365day_5m.csv",
    ]

    # Wallet credentials are optional (demo mode only by default)
    PRIVATE_KEY: str = os.getenv("PRIVATE_KEY", "")
    WALLET_ADDRESS: str = os.getenv("WALLET_ADDRESS", "")

    @classmethod
    def tokens(cls) -> Dict[str, Token]:
        """Return basic token metadata keyed by symbol."""

        return {
            "pDAI": Token("pDAI", cls.PDAI_ADDRESS, 18),
            "DAI": Token("DAI", cls.DAI_ADDRESS, 18),
            "WPLS": Token("WPLS", cls.WPLS_ADDRESS, 18),
        }

    @classmethod
    def resolve_ohlcv_path(cls) -> str:
        """Resolve an OHLCV CSV path based on preference order."""

        for candidate in cls.OHLCV_PREFERENCE:
            path = cls.DATA_DIR / candidate
            if path.exists():
                return str(path)
        return ""

    @classmethod
    def validate(cls) -> bool:
        """Basic sanity checks for configuration."""

        if cls.MA_SHORT_PERIOD >= cls.MA_LONG_PERIOD:
            raise ValueError("MA_SHORT_PERIOD must be less than MA_LONG_PERIOD")

        if not cls.DEMO_MODE and (not cls.PRIVATE_KEY or not cls.WALLET_ADDRESS):
            raise ValueError("PRIVATE_KEY and WALLET_ADDRESS must be set for live trading")

        return True


# Minimal ABIs reused across modules -----------------------------------------------------------
PULSEX_ROUTER_ABI = [
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

ERC20_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
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
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    }
]
