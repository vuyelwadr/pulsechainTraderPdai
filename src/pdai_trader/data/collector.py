"""
Real Historical pDAI Price Data Collector
Adapted from the HEX collector to track pDAI/WPLS pricing routed to DAI.
"""
from web3 import Web3
from web3._utils.events import get_event_data
import pandas as pd
from datetime import datetime, timedelta
import time
import warnings
from tqdm import tqdm
import concurrent.futures
import numpy as np
import pytz
import json
import os
import logging
from typing import Dict, List, Optional, Tuple

import os, sys
# Ensure repo root on sys.path so sibling packages import correctly when running direct scripts
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
from pdai_trader.config import Settings, PULSEX_ROUTER_ABI, ERC20_ABI
from pdai_trader.utils.rpc import RPCLoadBalancer

logger = logging.getLogger(__name__)

# Timezone configuration
LOCAL_TIMEZONE_OFFSET = 0  # UTC
LOCAL_TIMEZONE = pytz.UTC  
BLOCKCHAIN_TIMEZONE = pytz.UTC

class PdaiDataCollector:
    """Collects real historical pDAI price data from PulseChain blockchain"""
    
    def __init__(self):
        self.config = Settings
        self.rpc_balancer = None
        self.pdai_wpls_pair_address = None
        # Aggressive caching for maximum performance
        self.block_cache = {}
        self.price_cache = {}  # Cache price calculations
        self.swap_topic = None
        self._pair_contract = None
        self._pair_token0 = None
        self._pair_token1 = None
        self._pdai_decimals = None
        self._wpls_decimals = None
        self._dai_decimals = 18
        self._wpls_to_dai_cache: Dict[int, float] = {}
        
        # Domain-aware predictive search optimization
        self.avg_block_time = None
        self.latest_block_info = None
        
        self.connect_to_blockchain()
        self.find_pdai_wpls_pair()
        self._calculate_average_block_time()
        self._init_swap_event_support()
        
    def connect_to_blockchain(self):
        """Initialize RPC load balancer for maximum throughput"""
        try:
            self.rpc_balancer = RPCLoadBalancer()
            logger.info("🚀 RPC Load Balancer initialized - ready for maximum throughput!")
        except Exception as e:
            logger.error(f"Failed to initialize RPC load balancer: {e}")
            raise ConnectionError("RPC load balancer initialization failed")
    
    def find_pdai_wpls_pair(self):
        """Initialize pDAI/WPLS trading pair configuration"""
        # Load balancer handles contract instantiation internally
        logger.info("Using load balanced PulseX Router for pDAI/DAI price derivation via WPLS bridge")

    def _init_swap_event_support(self):
        """Set up minimal pair contract + Swap topic for OHLCV from real swaps"""
        try:
            # Default to configured pDAI/WPLS pair (fast path)
            pair_addr = Web3.to_checksum_address(self.config.PDAI_WPLS_POOL)
            self.pdai_wpls_pair_address = pair_addr

            # Minimal UniswapV2Pair ABI
            pair_abi = [
                {
                    "constant": True,
                    "inputs": [],
                    "name": "token0",
                    "outputs": [{"name": "", "type": "address"}],
                    "payable": False,
                    "stateMutability": "view",
                    "type": "function",
                },
                {
                    "constant": True,
                    "inputs": [],
                    "name": "token1",
                    "outputs": [{"name": "", "type": "address"}],
                    "payable": False,
                    "stateMutability": "view",
                    "type": "function",
                },
                {
                    "anonymous": False,
                    "inputs": [
                        {"indexed": True, "internalType": "address", "name": "sender", "type": "address"},
                        {"indexed": False, "internalType": "uint256", "name": "amount0In", "type": "uint256"},
                        {"indexed": False, "internalType": "uint256", "name": "amount1In", "type": "uint256"},
                        {"indexed": False, "internalType": "uint256", "name": "amount0Out", "type": "uint256"},
                        {"indexed": False, "internalType": "uint256", "name": "amount1Out", "type": "uint256"},
                        {"indexed": True, "internalType": "address", "name": "to", "type": "address"},
                    ],
                    "name": "Swap",
                    "type": "event",
                },
            ]

            # Use a primary endpoint for contract instantiation
            primary_w3 = self.rpc_balancer.endpoints[0].w3
            self._pair_contract = primary_w3.eth.contract(address=pair_addr, abi=pair_abi)
            self._pair_token0 = Web3.to_checksum_address(self._pair_contract.functions.token0().call())
            self._pair_token1 = Web3.to_checksum_address(self._pair_contract.functions.token1().call())

            # Confirm tokens are pDAI/WPLS
            addr_pdai = Web3.to_checksum_address(self.config.PDAI_ADDRESS)
            addr_wpls = Web3.to_checksum_address(self.config.WPLS_ADDRESS)
            addr_dai = Web3.to_checksum_address(self.config.DAI_ADDRESS)
            if {self._pair_token0, self._pair_token1} != {addr_pdai, addr_wpls}:
                logger.warning(
                    f"Configured pair {pair_addr} not pDAI/WPLS: token0={self._pair_token0}, token1={self._pair_token1}"
                )

            # Get decimals from token contracts (accuracy)
            erc20 = lambda addr: primary_w3.eth.contract(address=addr, abi=ERC20_ABI)
            self._pdai_decimals = erc20(addr_pdai).functions.decimals().call()
            self._wpls_decimals = erc20(addr_wpls).functions.decimals().call()
            try:
                self._dai_decimals = erc20(addr_dai).functions.decimals().call()
            except Exception:
                self._dai_decimals = 18

            # Swap topic HexBytes
            self.swap_topic = primary_w3.keccak(text="Swap(address,uint256,uint256,uint256,uint256,address)")
            logger.info("Swap event support initialized for OHLCV collection")
        except Exception as e:
            logger.error(f"Failed to init swap event support: {e}")
    
    def _calculate_average_block_time(self):
        """Calculate average block time for predictive search optimization"""
        try:
            # Get latest block using load balancer
            latest_block = self.rpc_balancer.get_latest_block_number()
            latest_timestamp = self.get_block_timestamp(latest_block)
            
            # Get block from 2 days ago to calculate average
            blocks_back = 17280  # ~2 days worth of blocks (assuming 10s block time)
            past_block = max(1, latest_block - blocks_back)
            past_timestamp = self.get_block_timestamp(past_block)
            
            if latest_timestamp and past_timestamp:
                time_diff = latest_timestamp - past_timestamp
                block_diff = latest_block - past_block
                self.avg_block_time = time_diff / block_diff
                
                self.latest_block_info = {
                    'block': latest_block,
                    'timestamp': latest_timestamp
                }
                
                logger.info(f"Calculated average block time: {self.avg_block_time:.2f} seconds")
                logger.info(f"Latest block info: {latest_block} at {datetime.fromtimestamp(latest_timestamp)}")
            else:
                logger.warning("Failed to calculate average block time, using default 10s")
                self.avg_block_time = 10.0  # Default PulseChain block time
                
        except Exception as e:
            logger.warning(f"Error calculating average block time: {e}, using default 10s")
            self.avg_block_time = 10.0
    
    def get_block_timestamp(self, block_num):
        """Get block timestamp with caching using load balancer"""
        if block_num in self.block_cache:
            return self.block_cache[block_num]
        
        try:
            timestamp = self.rpc_balancer.get_block_timestamp(block_num)
            if timestamp:
                self.block_cache[block_num] = timestamp
            return timestamp
        except Exception as e:
            logger.error(f"Error getting block {block_num}: {e}")
            return None
    
    def timestamp_to_datetime(self, timestamp):
        """Convert blockchain timestamp to datetime in UTC"""
        return datetime.fromtimestamp(timestamp, tz=BLOCKCHAIN_TIMEZONE)
    
    def find_block_for_time(self, target_time, latest_block=None):
        """
        Find block close to target time using binary search
        REVERTED: Simple and fast - focus on RPC throughput, not algorithm complexity
        """
        if target_time.tzinfo is None:
            target_time = LOCAL_TIMEZONE.localize(target_time)
        
        target_time_utc = target_time.astimezone(BLOCKCHAIN_TIMEZONE)
        
        if not latest_block:
            latest_block = self.rpc_balancer.get_latest_block_number()
        
        target_unix = int(target_time_utc.timestamp())
        
        # Simple binary search boundaries
        left = 1
        right = latest_block
        closest_block = None
        min_diff = float('inf')
        
        while left <= right:
            mid = (left + right) // 2
            
            try:
                mid_timestamp = self.get_block_timestamp(mid)
                if mid_timestamp is None:
                    right = mid - 1
                    continue
                
                # Update closest block
                diff = abs(mid_timestamp - target_unix)
                if diff < min_diff:
                    min_diff = diff
                    closest_block = mid
                
                # Adjust search range
                if mid_timestamp < target_unix:
                    left = mid + 1
                else:
                    right = mid - 1
                    
            except Exception as e:
                logger.warning(f"Error checking block {mid}: {e}")
                right = mid - 1
        
        return closest_block if closest_block is not None else latest_block

    def _get_wpls_to_dai_rate(self, block_num: int) -> Optional[float]:
        if block_num in self._wpls_to_dai_cache:
            return self._wpls_to_dai_cache[block_num]

        try:
            amount_in = 10 ** self._wpls_decimals
            path = [self.config.WPLS_ADDRESS, self.config.DAI_ADDRESS]
            amounts_out = self.rpc_balancer.get_amounts_out_at_block(
                PULSEX_ROUTER_ABI,
                self.config.PULSEX_ROUTER_V2,
                amount_in,
                path,
                block_num
            )
            dai_amount = amounts_out[-1]
            rate = dai_amount / (10 ** self._dai_decimals)
            self._wpls_to_dai_cache[block_num] = rate
            return rate
        except Exception as e:
            logger.warning(f"Failed to fetch WPLS→DAI rate at block {block_num}: {e}")
            return None

    def get_pdai_price_at_block(self, block_num):
        """Get pDAI price denominated in DAI at a specific block."""
        # Check cache first
        if block_num in self.price_cache:
            return self.price_cache[block_num]
        
        try:
            # Amount of pDAI to check (1 pDAI = 10^18 units)
            pdai_amount = 10**18  # 1 pDAI (18 decimals)
            
            # Get amounts out for 1 pDAI -> WPLS -> DAI using load balancer
            path = [self.config.PDAI_ADDRESS, self.config.WPLS_ADDRESS, self.config.DAI_ADDRESS]
            amounts_out = self.rpc_balancer.get_amounts_out_at_block(
                PULSEX_ROUTER_ABI, 
                self.config.PULSEX_ROUTER_V2,
                pdai_amount, 
                path, 
                block_num
            )
            
            # Calculate price (DAI per pDAI)
            dai_amount = amounts_out[-1]
            price = dai_amount / (10 ** self._dai_decimals)
            
            # Cache the result
            self.price_cache[block_num] = price
            
            return price
            
        except Exception as e:
            logger.error(f"Error getting pDAI price at block {block_num}: {e}")
            return None

    def get_data_for_timestamp(self, target_time, latest_block=None):
        """Get pDAI price data for a specific timestamp."""
        if not latest_block:
            latest_block = self.rpc_balancer.get_latest_block_number()
        
        try:
            # Find block close to target time
            block_num = self.find_block_for_time(target_time, latest_block)
            
            # Get pDAI price at that block
            price = self.get_pdai_price_at_block(block_num)
            
            if price is None:
                return None
            
            # Get actual block time
            block_timestamp = self.get_block_timestamp(block_num)
            block_time = self.timestamp_to_datetime(block_timestamp)
            
            # Convert target time to UTC for comparison
            if target_time.tzinfo is None:
                target_time_utc = LOCAL_TIMEZONE.localize(target_time).astimezone(BLOCKCHAIN_TIMEZONE)
            else:
                target_time_utc = target_time.astimezone(BLOCKCHAIN_TIMEZONE)
            
            # Calculate time difference
            time_diff = abs((block_time - target_time_utc).total_seconds())
            
            return {
                'timestamp': target_time,
                'block': block_num, 
                'block_timestamp': block_time,
                'price': price,
                'time_diff_seconds': time_diff
            }
            
        except Exception as e:
            logger.error(f"Error processing timestamp {target_time}: {e}")
            return None
    
    def get_latest_price(self):
        """Get the latest pDAI price quoted in DAI."""
        try:
            latest_block = self.rpc_balancer.get_latest_block_number()
            logger.info(f"Getting latest pDAI price at block {latest_block}")
            
            # Get block timestamp
            block_timestamp = self.get_block_timestamp(latest_block)
            block_time_utc = self.timestamp_to_datetime(block_timestamp)
            
            # Get current price
            price = self.get_pdai_price_at_block(latest_block)
            
            if price is None:
                return None
            
            logger.info(f"Latest pDAI price: {price:.8f} DAI per pDAI at block {latest_block}")
            
            return {
                'block': latest_block,
                'time_utc': block_time_utc,
                'price': price
            }
            
        except Exception as e:
            logger.error(f"Error getting latest pDAI price: {e}")
            return None

    # =============================
    # Real OHLCV from Swap Events
    # =============================
    def _get_logs_safe(self, w3: Web3, from_block: int, to_block: int, min_chunk: int = 200):
        """Fetch logs with adaptive splitting to avoid RPC timeouts."""
        try:
            return w3.eth.get_logs(
                {
                    "fromBlock": from_block,
                    "toBlock": to_block,
                    "address": self.pdai_wpls_pair_address,
                    "topics": [self.swap_topic],
                }
            )
        except Exception as e:
            msg = str(e).lower()
            span = to_block - from_block + 1
            if (
                "timeout" in msg
                or "query timeout" in msg
                or "log response size" in msg
                or "request entity too large" in msg
                or "limit" in msg
            ) and span > 1:
                mid = from_block + span // 2
                next_min = max(10, min_chunk // 2) if span <= min_chunk else min_chunk
                left = self._get_logs_safe(w3, from_block, mid, next_min)
                right = self._get_logs_safe(w3, mid + 1, to_block, next_min)
                return left + right
            raise

    def _decode_swaps(self, w3: Web3, logs: List[Dict]) -> List[Dict]:
        """Fast decode of Swap logs by parsing data (4 x uint256)."""
        from hexbytes import HexBytes
        decoded = []
        for log in logs:
            try:
                data = log.get("data")
                if isinstance(data, HexBytes):
                    b = bytes(data)
                else:
                    # hex string like '0x...'
                    b = Web3.to_bytes(hexstr=data)
                if len(b) < 32 * 4:
                    continue
                amount0In = int.from_bytes(b[0:32], byteorder="big")
                amount1In = int.from_bytes(b[32:64], byteorder="big")
                amount0Out = int.from_bytes(b[64:96], byteorder="big")
                amount1Out = int.from_bytes(b[96:128], byteorder="big")
                decoded.append(
                    {
                        "blockNumber": log["blockNumber"],
                        "amount0In": amount0In,
                        "amount1In": amount1In,
                        "amount0Out": amount0Out,
                        "amount1Out": amount1Out,
                    }
                )
            except Exception:
                continue
        return decoded

    def _swap_price_and_volume(self, swap: Dict, wpls_to_dai: Optional[float]) -> Tuple[Optional[float], float, float]:
        a0i, a1i = swap["amount0In"], swap["amount1In"]
        a0o, a1o = swap["amount0Out"], swap["amount1Out"]
        addr_pdai = Web3.to_checksum_address(self.config.PDAI_ADDRESS)
        pdai_is_token0 = self._pair_token0 == addr_pdai

        price = None
        if pdai_is_token0:
            if a0i > 0 and a1o > 0:
                price = (a1o / (10 ** self._wpls_decimals)) / (a0i / (10 ** self._pdai_decimals))
            elif a1i > 0 and a0o > 0:
                price = (a1i / (10 ** self._wpls_decimals)) / (a0o / (10 ** self._pdai_decimals))
            vol_pdai = (a0i + a0o) / (10 ** self._pdai_decimals)
            vol_wpls = (a1i + a1o) / (10 ** self._wpls_decimals)
        else:
            if a1i > 0 and a0o > 0:
                price = (a0o / (10 ** self._wpls_decimals)) / (a1i / (10 ** self._pdai_decimals))
            elif a0i > 0 and a1o > 0:
                price = (a0i / (10 ** self._wpls_decimals)) / (a1o / (10 ** self._pdai_decimals))
            vol_pdai = (a1i + a1o) / (10 ** self._pdai_decimals)
            vol_wpls = (a0i + a0o) / (10 ** self._wpls_decimals)

        price_dai = None
        vol_dai = None
        if price is not None and wpls_to_dai is not None:
            price_dai = price * wpls_to_dai
            vol_dai = vol_wpls * wpls_to_dai

        return price_dai, vol_pdai, vol_dai if vol_dai is not None else 0.0

    def _prefetch_wpls_to_dai_rates(self, blocks: List[int]) -> Dict[int, Optional[float]]:
        """Fetch WPLS→DAI conversion once per block using the load balancer."""
        missing = [b for b in blocks if b not in self._wpls_to_dai_cache]
        if missing:
            logger.info("Fetching WPLS→DAI quotes for %s blocks", len(missing))
            amount_in = 10 ** self._wpls_decimals
            path = [self.config.WPLS_ADDRESS, self.config.DAI_ADDRESS]

            def fetch(block: int) -> Tuple[int, Optional[float]]:
                try:
                    amounts = self.rpc_balancer.get_amounts_out_at_block(
                        PULSEX_ROUTER_ABI,
                        self.config.PULSEX_ROUTER_V2,
                        amount_in,
                        path,
                        block,
                    )
                    rate = amounts[-1] / (10 ** self._dai_decimals)
                    return block, rate
                except Exception as exc:
                    logger.debug(f"Failed WPLS→DAI quote at block {block}: {exc}")
                    return block, None

            max_workers = min(32, max(4, len(missing) // 20 or 1))
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                for idx, (blk, rate) in enumerate(executor.map(fetch, missing), 1):
                    self._wpls_to_dai_cache[blk] = rate
                    if idx % 200 == 0 or idx == len(missing):
                        logger.info("  • fetched %s/%s WPLS→DAI quotes", idx, len(missing))

        return {b: self._wpls_to_dai_cache.get(b) for b in blocks}

    def collect_ohlcv_from_swaps(self, start_time, end_time=None, interval_minutes: int = 5, volume_asset: str = 'pDAI') -> pd.DataFrame:
        """Collect true OHLCV by aggregating PulseX Swap events for pDAI priced in DAI (via pDAI→WPLS→DAI routing)."""
        if end_time is None:
            end_time = datetime.now(tz=BLOCKCHAIN_TIMEZONE)

        # Ensure tz aware UTC
        if start_time.tzinfo is None:
            start_time = LOCAL_TIMEZONE.localize(start_time)
        if end_time.tzinfo is None:
            end_time = LOCAL_TIMEZONE.localize(end_time)
        start_time = start_time.astimezone(BLOCKCHAIN_TIMEZONE)
        end_time = end_time.astimezone(BLOCKCHAIN_TIMEZONE)

        # Determine block bounds quickly
        latest_block = self.rpc_balancer.get_latest_block_number()
        start_block = self.find_block_for_time(start_time, latest_block)
        end_block = self.find_block_for_time(end_time, latest_block)
        if end_block < start_block:
            start_block, end_block = end_block, start_block

        span = end_block - start_block + 1
        logger.info(
            "Preparing swap scan from block %s to %s (~%s blocks) for %s to %s",
            start_block,
            end_block,
            span,
            start_time,
            end_time,
        )

        # Build chunk ranges and fetch in parallel across endpoints
        # More aggressive chunk sizing with safe fallback splitting on timeouts.
        # Aim for ~12 chunks, cap between 10k and 150k blocks per request.
        target_chunks = 8
        chunk_size = span // target_chunks if span > target_chunks else span
        chunk_size = max(10_000, min(200_000, chunk_size))
        # For very long ranges, keep chunk size moderate to avoid RPC timeouts
        if chunk_size > 5_000:
            chunk_size = 5_000
        ranges = []
        b = start_block
        while b <= end_block:
            e = min(b + chunk_size - 1, end_block)
            ranges.append((b, e))
            b = e + 1

        logger.info("Created %s block chunks (chunk size ≈ %s blocks)", len(ranges), chunk_size)

        # Parallel log fetching
        import concurrent.futures
        all_swaps = []

        def fetch_range(args):
            fb, tb, endpoint_idx = args
            ep = self.rpc_balancer.endpoints[endpoint_idx % len(self.rpc_balancer.endpoints)]
            logs = self._get_logs_safe(ep.w3, fb, tb)
            if not logs:
                return []
            return self._decode_swaps(ep.w3, logs)

        # Assign endpoints round-robin
        tasks = [(r[0], r[1], i) for i, r in enumerate(ranges)]

        max_workers = min(16, max(8, len(tasks) // 40 or 8))
        logger.info("Fetching swap logs with %s workers", max_workers)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            for idx, res in enumerate(ex.map(fetch_range, tasks), 1):
                if res:
                    all_swaps.extend(res)
                if idx % 5 == 0 or idx == len(tasks):
                    logger.info("  • processed %s/%s chunks (%s swaps)", idx, len(tasks), len(all_swaps))

        if not all_swaps:
            logger.warning("No swap events found for requested window")
            return pd.DataFrame()

        # Unique blocks for timestamps
        unique_blocks = sorted({s['blockNumber'] for s in all_swaps})
        logger.info("Collected %s swaps across %s blocks", len(all_swaps), len(unique_blocks))

        # Parallel fetch of block timestamps (uses load balancer and cache)
        def fetch_ts(bn):
            return bn, self.get_block_timestamp(bn)

        block_ts = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=64) as ex:
            for idx, (bn, ts) in enumerate(ex.map(fetch_ts, unique_blocks), 1):
                block_ts[bn] = ts
                if idx % 200 == 0 or idx == len(unique_blocks):
                    logger.info("  • resolved %s/%s block timestamps", idx, len(unique_blocks))

        logger.info(f"Decoded {len(all_swaps)} swaps across {len(unique_blocks)} blocks")

        # Prefetch WPLS→DAI conversion per block to avoid per-swap router calls
        block_rates = self._prefetch_wpls_to_dai_rates(unique_blocks)

        rows = []
        start_unix = int(start_time.timestamp())
        end_unix = int(end_time.timestamp())
        for idx, sw in enumerate(all_swaps, 1):
            ts = block_ts.get(sw['blockNumber'])
            if ts is None or ts < start_unix or ts > end_unix:
                continue
            price, vol_pdai, vol_dai = self._swap_price_and_volume(
                sw,
                block_rates.get(sw['blockNumber'])
            )
            if price is None:
                continue
            rows.append({
                'timestamp': datetime.fromtimestamp(ts, tz=BLOCKCHAIN_TIMEZONE),
                'price': price,
                'volume_pdai': vol_pdai,
                'volume_dai': vol_dai
            })
            if idx % 1000 == 0 or idx == len(all_swaps):
                logger.info("  • processed %s/%s swaps into rows", idx, len(all_swaps))

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows).set_index('timestamp')
        asset = volume_asset.strip().upper()
        vol_col = 'volume_pdai' if asset == 'PDAI' else 'volume_dai'
        freq = f"{int(interval_minutes)}min"
        ohlcv = df.resample(freq).agg({
            'price': ['first', 'max', 'min', 'last'],
            vol_col: 'sum'
        })
        # Flatten columns
        ohlcv.columns = ['open', 'high', 'low', 'close', 'volume']
        ohlcv = ohlcv.dropna(subset=['open', 'high', 'low', 'close'])
        ohlcv.reset_index(inplace=True)
        # Add 'price' equal to close for compatibility
        ohlcv['price'] = ohlcv['close']
        return ohlcv
    
    def collect_historical_data(self, start_time, end_time=None, interval_minutes=15):
        """
        Collect historical pDAI price data
        
        Args:
            start_time: Start datetime (timezone-aware)
            end_time: End datetime (if None, uses current time)
            interval_minutes: Data collection interval in minutes
        """
        if end_time is None:
            end_time = datetime.now(tz=BLOCKCHAIN_TIMEZONE)
        
        # Ensure timezone awareness
        if start_time.tzinfo is None:
            start_time = LOCAL_TIMEZONE.localize(start_time)
        if end_time.tzinfo is None:
            end_time = LOCAL_TIMEZONE.localize(end_time)
        
        logger.info(f"Collecting pDAI historical data from {start_time} to {end_time}")
        
        # Create timestamp intervals
        timestamps = []
        current_time = start_time
        while current_time <= end_time:
            timestamps.append(current_time)
            current_time += timedelta(minutes=interval_minutes)
        
        logger.info(f"Created {len(timestamps)} intervals to process")
        
        # Get latest block for efficiency using load balancer
        latest_block = self.rpc_balancer.get_latest_block_number()
        
        # MAXIMUM THROUGHPUT FOCUS - RPC is the bottleneck, not CPU
        # Use many more workers for I/O bound blockchain calls
        max_workers = min(40, max(20, len(timestamps) // 10))  # Push to 40 workers for I/O
        batch_size = 1000  # Massive batches for maximum throughput
        
        data = []
        progress_bar = tqdm(total=len(timestamps), desc="Collecting pDAI price data")
        
        for i in range(0, len(timestamps), batch_size):
            batch = timestamps[i:min(i+batch_size, len(timestamps))]
            
            # Process batch in parallel with maximum workers
            batch_results = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(self.get_data_for_timestamp, ts, latest_block) for ts in batch]
                
                for future in concurrent.futures.as_completed(futures):
                    try:
                        result = future.result()
                        if result:
                            batch_results.append(result)
                    except Exception as e:
                        logger.error(f"Error in parallel processing: {e}")
            
            data.extend(batch_results)
            progress_bar.update(len(batch))
            
            # NO DELAYS - Maximum throughput
        
        progress_bar.close()
        
        if not data:
            logger.error("No historical data collected")
            return None
        
        # Create DataFrame
        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['block_timestamp'] = pd.to_datetime(df['block_timestamp'])
        
        # Add precision metrics
        df['time_diff_minutes'] = df['time_diff_seconds'] / 60
        df['potentially_inaccurate'] = df['time_diff_minutes'] > 15
        
        # Set timestamp as index and sort
        df.set_index('timestamp', inplace=True)
        df = df.sort_index()
        
        # Generate filename
        start_str = df.index.min().strftime('%Y%m%d_%H%M')
        end_str = df.index.max().strftime('%Y%m%d_%H%M')
        filename = f'data/hex_historical_data_{start_str}_to_{end_str}.csv'
        
        # Create data directory if it doesn't exist
        os.makedirs('data', exist_ok=True)
        
        # Save to CSV
        df.to_csv(filename)
        
        # Log statistics
        inaccurate_count = df['potentially_inaccurate'].sum()
        inaccurate_pct = (inaccurate_count / len(df)) * 100
        
        logger.info(f"Collected {len(df)} pDAI price data points")
        logger.info(f"Success rate: {len(df)/len(timestamps)*100:.1f}%")
        logger.info(f"Average time difference: {df['time_diff_minutes'].mean():.1f} minutes")
        logger.info(f"Potentially inaccurate points: {inaccurate_count} ({inaccurate_pct:.1f}%)")
        logger.info(f"Data saved to: {filename}")
        
        return df
    
    def collect_incremental_data(self, cache_file: str = None) -> pd.DataFrame:
        """
        Collect incremental data - only fetch new data since last collection
        
        Args:
            cache_file: Path to existing data cache file
            
        Returns:
            Updated DataFrame with new data appended
        """
        if cache_file is None:
            cache_file = 'data/hex_price_history_dai.csv'
        
        # Load existing data if it exists
        existing_data = None
        last_timestamp = None
        
        if os.path.exists(cache_file):
            try:
                existing_data = pd.read_csv(cache_file)
                existing_data['timestamp'] = pd.to_datetime(existing_data['timestamp'])
                last_timestamp = existing_data['timestamp'].max()
                logger.info(f"Found existing data ending at: {last_timestamp}")
            except Exception as e:
                logger.warning(f"Error loading existing data: {e}")
                existing_data = None
        
        # Determine collection start time
        end_time = datetime.now(tz=BLOCKCHAIN_TIMEZONE)
        
        if last_timestamp is not None:
            # Start from 5 minutes after last data point to avoid duplicates
            start_time = last_timestamp + timedelta(minutes=5)
            
            # Check if we need to collect any new data
            if start_time >= end_time:
                logger.info("Data is already up to date")
                return existing_data if existing_data is not None else pd.DataFrame()
        else:
            # No existing data - collect 1 year of historical data
            start_time = end_time - timedelta(days=365)
            logger.info("No existing data found - collecting 1 year of historical data")
        
        logger.info(f"Collecting incremental data from {start_time} to {end_time}")
        
        # Collect new data using 5-minute intervals
        new_data = self.collect_historical_data(
            start_time=start_time,
            end_time=end_time,
            interval_minutes=5
        )
        
        if new_data is None or new_data.empty:
            logger.warning("No new data collected")
            return existing_data if existing_data is not None else pd.DataFrame()
        
        # Combine existing and new data
        if existing_data is not None and not existing_data.empty:
            # Ensure timestamp is not in index for concat
            if 'timestamp' not in existing_data.columns:
                existing_data.reset_index(inplace=True)
            if 'timestamp' not in new_data.columns:
                new_data.reset_index(inplace=True)
            
            # Combine data
            combined_data = pd.concat([existing_data, new_data], ignore_index=True)
            
            # Remove duplicates based on timestamp
            combined_data = combined_data.drop_duplicates(subset=['timestamp'], keep='last')
            combined_data = combined_data.sort_values('timestamp').reset_index(drop=True)
            
            logger.info(f"Combined data: {len(existing_data)} existing + {len(new_data)} new = {len(combined_data)} total points")
        else:
            combined_data = new_data
            logger.info(f"Using new data: {len(combined_data)} points")
        
        # Save updated data to cache
        try:
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            combined_data.to_csv(cache_file, index=False)
            logger.info(f"Updated cache saved to: {cache_file}")
        except Exception as e:
            logger.error(f"Error saving updated cache: {e}")
        
        return combined_data

def main():
    """Simple CLI smoke-check for the pDAI data collector."""
    collector = PdaiDataCollector()
    
    # Get latest price first
    latest = collector.get_latest_price()
    if latest:
        print(f"Current pDAI price: {latest['price']:.6f} DAI per pDAI")
    
    # Collect last 24 hours of data as test
    end_time = datetime.now(tz=BLOCKCHAIN_TIMEZONE)
    start_time = end_time - timedelta(hours=24)
    
    df = collector.collect_historical_data(start_time, end_time, interval_minutes=60)
    
    if df is not None:
        print(f"\nCollected {len(df)} data points")
        print(f"Price range: {df['price'].min():.6f} - {df['price'].max():.6f} DAI per pDAI")
        print(f"Price change: {((df['price'].iloc[-1] / df['price'].iloc[0]) - 1) * 100:+.2f}%")

if __name__ == "__main__":
    main()
