"""
Data Handler for PDAI Trading Bot
Manages price data fetching and historical data management
"""
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import logging
import pytz
from web3 import Web3
from typing import Optional, Dict, List
import os, sys
# Ensure repo root on sys.path so sibling packages import when running bot/*.py directly
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
from bot.config import Config, PULSEX_ROUTER_ABI, ERC20_ABI
from collectors.pdai_data_collector import PdaiDataCollector
import os

logger = logging.getLogger(__name__)

class DataHandler:
    """Handles data fetching and management for PDAI trading"""
    
    def __init__(self):
        self.config = Config()
        self.w3 = None
        self.router_contract = None
        self.pdai_contract = None
        self.wpls_contract = None
        self.dai_contract = None
        self._dai_decimals = 18
        self.price_history = pd.DataFrame()
        self.pdai_collector = None
        
        # Ensure data directory exists
        os.makedirs(self.config.DATA_DIR, exist_ok=True)
        
        self._connect_to_blockchain()
        self._initialize_pdai_collector()
        
    def _connect_to_blockchain(self):
        """Connect to PulseChain blockchain"""
        try:
            self.w3 = Web3(Web3.HTTPProvider(self.config.RPC_URL))
            
            if not self.w3.is_connected():
                logger.error("Failed to connect to PulseChain")
                raise ConnectionError("Cannot connect to PulseChain RPC")
            
            # Initialize contracts
            self.router_contract = self.w3.eth.contract(
                address=self.config.PULSEX_ROUTER_V2,
                abi=PULSEX_ROUTER_ABI
            )
            
            self.pdai_contract = self.w3.eth.contract(
                address=self.config.PDAI_ADDRESS,
                abi=ERC20_ABI
            )
            
            self.wpls_contract = self.w3.eth.contract(
                address=self.config.WPLS_ADDRESS,
                abi=ERC20_ABI
            )

            self.dai_contract = self.w3.eth.contract(
                address=self.config.DAI_ADDRESS,
                abi=ERC20_ABI
            )

            try:
                self._dai_decimals = self.dai_contract.functions.decimals().call()
            except Exception:
                self._dai_decimals = 18
            
            logger.info("Successfully connected to PulseChain")
            
        except Exception as e:
            logger.error(f"Failed to connect to blockchain: {e}")
            # Even in demo mode, we need real price data
            logger.error("Cannot run without blockchain connection - need real price data")
            raise ConnectionError(f"Blockchain connection required for real price data: {e}")
    
    def _initialize_pdai_collector(self):
        """Initialize PDAI data collector for real historical data"""
        try:
            self.pdai_collector = PdaiDataCollector()
            logger.info("PDAI data collector initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize PDAI data collector: {e}")
            logger.warning("Will fall back to simulated historical data if needed")
            self.pdai_collector = None
    
    def get_current_price(self) -> Optional[float]:
        """Get current PDAI/DAI price from PulseX via PDAI→WPLS→DAI routing."""
        try:
            if not self.w3 or not self.w3.is_connected():
                logger.error("No blockchain connection available - cannot get real price data")
                return None
            
            # Path: PDAI -> WPLS -> DAI
            path = [self.config.PDAI_ADDRESS, self.config.WPLS_ADDRESS, self.config.DAI_ADDRESS]

            # Get amount out for 1 PDAI (18 decimals)
            pdai_amount_in = 10**18
            
            amounts_out = self.router_contract.functions.getAmountsOut(
                pdai_amount_in, path
            ).call()
            
            # Convert output amount to DAI price (18 decimals for DAI)
            dai_amount_out = amounts_out[-1]
            price = dai_amount_out / (10 ** self._dai_decimals)
            
            logger.debug(f"Current PDAI price: {price:.8f} DAI")
            return price
            
        except Exception as e:
            logger.error(f"Error fetching current price: {e}")
            # NEVER return simulated data - we need real price data always
            return None
    
    
    def fetch_historical_data(self, days: int = None, use_incremental: bool = True) -> pd.DataFrame:
        """Fetch historical OHLCV data (real swaps; no synthetic)."""
        if days is None:
            days = self.config.BACKTEST_DAYS
            
        logger.info(f"Fetching {days} days of historical data")
        
        cache_file = os.path.join(self.config.DATA_DIR, "pdai_price_history_dai.csv")
        
        # Always fetch real data - demo mode only affects trading execution, not data
        if not self.w3 or not self.w3.is_connected():
            logger.error("Cannot fetch historical data without blockchain connection")
            return pd.DataFrame()
        
        if use_incremental and self.pdai_collector is not None:
            # Incremental OHLCV: compute from last timestamp to now using swaps
            logger.info("Using incremental OHLCV collection from swap events")
            existing_data = None
            last_ts = None
            if os.path.exists(cache_file):
                try:
                    existing_data = pd.read_csv(cache_file)
                    existing_data['timestamp'] = pd.to_datetime(existing_data['timestamp'])
                    if not existing_data.empty:
                        last_ts = existing_data['timestamp'].max()
                except Exception as e:
                    logger.warning(f"Error reading cache file: {e}")
                    existing_data = None
            end_time = datetime.now(tz=pytz.UTC)
            if last_ts is None:
                start_time = end_time - timedelta(days=min(days, 365))
                logger.info("No cache present; collecting fresh OHLCV")
            else:
                start_time = last_ts + timedelta(minutes=5)
                if start_time >= end_time:
                    logger.info("Cache is up to date; returning cached OHLCV")
                    self.price_history = existing_data if existing_data is not None else pd.DataFrame()
                    return self.price_history
            new_df = self.pdai_collector.collect_ohlcv_from_swaps(
                start_time=start_time,
                end_time=end_time,
                interval_minutes=5,
                volume_asset='PDAI'
            )
            if new_df is None or new_df.empty:
                logger.warning("No new OHLCV data collected; using cache if available")
                self.price_history = existing_data if existing_data is not None else pd.DataFrame()
                return self.price_history
            if existing_data is not None and not existing_data.empty:
                combined = pd.concat([existing_data, new_df], ignore_index=True)
                combined.drop_duplicates(subset=['timestamp'], keep='last', inplace=True)
                combined.sort_values('timestamp', inplace=True)
                self.price_history = combined.reset_index(drop=True)
            else:
                self.price_history = new_df.reset_index(drop=True)
            # Filter by days if needed
            if days is not None:
                cutoff = datetime.now(tz=pytz.UTC) - timedelta(days=days)
                self.price_history = self.price_history[
                    pd.to_datetime(self.price_history['timestamp'], utc=True) >= cutoff
                ]
            logger.info(f"Incremental OHLCV collection complete: {len(self.price_history)} candles")
            # Save cache
            try:
                self.price_history.to_csv(cache_file, index=False)
            except Exception as e:
                logger.warning(f"Failed to write cache: {e}")
            return self.price_history
        
        # Fallback to standard method (full OHLCV backfill)
        self.price_history = self._fetch_real_historical_data(days)
        
        # Save to cache
        try:
            self.price_history.to_csv(cache_file, index=False)
            logger.info(f"Cached historical data to {cache_file}")
        except Exception as e:
            logger.warning(f"Error caching data: {e}")
        
        return self.price_history
    
    
    def _fetch_real_historical_data(self, days: int) -> pd.DataFrame:
        """Fetch real historical OHLCV from blockchain swap events"""
        logger.info(f"Fetching real historical data from PulseChain for {days} days")
        
        try:
            if self.pdai_collector is not None:
                end_time = datetime.now(tz=pytz.UTC)
                start_time = end_time - timedelta(days=days)
                logger.info(f"Collecting real PDAI OHLCV from {start_time} to {end_time}")
                df = self.pdai_collector.collect_ohlcv_from_swaps(
                    start_time=start_time,
                    end_time=end_time,
                    interval_minutes=5,
                    volume_asset='PDAI'
                )
                if df is not None and not df.empty:
                    logger.info(f"Successfully collected {len(df)} OHLCV candles")
                    # Ensure required columns
                    if 'price' not in df.columns and 'close' in df.columns:
                        df['price'] = df['close']
                    return df
                else:
                    logger.error("Failed to collect real OHLCV - returning empty DataFrame")
                    return pd.DataFrame()
            else:
                logger.error("PDAI data collector not available - CANNOT proceed without real data")
                return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error fetching real historical data: {e}")
            return pd.DataFrame()
    
    def add_price_point(self, price: float, volume: float = 0):
        """Add a new price point to the historical data"""
        new_point = pd.DataFrame({
            'timestamp': [datetime.now()],
            'price': [price],
            'volume': [volume],
            'high': [price],
            'low': [price],
            'open': [price],
            'close': [price]
        })
        
        if self.price_history.empty:
            self.price_history = new_point
        else:
            self.price_history = pd.concat([self.price_history, new_point], ignore_index=True)
            
            # Keep only recent data to manage memory
            if len(self.price_history) > 100000:  # Keep last 100k points
                self.price_history = self.price_history.tail(50000)
    
    def get_latest_data(self, periods: int = 100) -> pd.DataFrame:
        """Get the latest N periods of data"""
        if self.price_history.empty:
            self.fetch_historical_data()
        
        return self.price_history.tail(periods)
    
    def save_data(self, filename: str = None):
        """Save current price history to file"""
        if filename is None:
            filename = os.path.join(self.config.DATA_DIR, f"pdai_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        
        if not self.price_history.empty:
            self.price_history.to_csv(filename, index=False)
            logger.info(f"Data saved to {filename}")
        else:
            logger.warning("No data to save")
    
    def load_data(self, filename: str):
        """Load price history from file"""
        try:
            self.price_history = pd.read_csv(filename)
            self.price_history['timestamp'] = pd.to_datetime(self.price_history['timestamp'])
            logger.info(f"Loaded {len(self.price_history)} data points from {filename}")
        except Exception as e:
            logger.error(f"Error loading data from {filename}: {e}")
            raise
    
    def get_price_stats(self) -> Dict:
        """Get basic price statistics"""
        if self.price_history.empty:
            return {}
        
        recent_data = self.price_history.tail(1440)  # Last 24 hours if minute data
        
        return {
            'current_price': self.price_history['price'].iloc[-1],
            '24h_high': recent_data['high'].max(),
            '24h_low': recent_data['low'].min(),
            '24h_change': (self.price_history['price'].iloc[-1] / recent_data['price'].iloc[0] - 1) * 100,
            '24h_volume': recent_data['volume'].sum(),
            'data_points': len(self.price_history)
        }
