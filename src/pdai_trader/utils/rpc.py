"""
Intelligent RPC Load Balancer for Maximum Throughput
Bypasses rate limiting by rotating between multiple endpoints
"""
import time
import logging
from threading import Lock
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor
from web3 import Web3
from dataclasses import dataclass

from pdai_trader.config import Settings

logger = logging.getLogger(__name__)

@dataclass
class RPCEndpoint:
    """Single RPC endpoint with performance tracking"""
    url: str
    w3: Optional[Web3] = None
    last_used: float = 0
    response_times: List[float] = None
    failure_count: int = 0
    is_healthy: bool = True
    cooldown_until: float = 0.0
    
    def __post_init__(self):
        if self.response_times is None:
            self.response_times = []
    
    @property
    def avg_response_time(self) -> float:
        """Average response time over last 10 requests"""
        if not self.response_times:
            return 0.0
        recent = self.response_times[-10:]
        return sum(recent) / len(recent)
    
    @property
    def is_rate_limited(self) -> bool:
        """Detect if endpoint is rate limited (slow responses)"""
        return self.avg_response_time > 2.0  # >2s suggests rate limiting
    
    def record_response(self, response_time: float, success: bool = True):
        """Record response time and success/failure"""
        self.response_times.append(response_time)
        if len(self.response_times) > 20:  # Keep only recent history
            self.response_times = self.response_times[-20:]
        
        if success:
            self.failure_count = max(0, self.failure_count - 1)
            self.cooldown_until = 0.0
        else:
            self.failure_count += 1
        
        # Mark unhealthy after 3 consecutive failures
        self.is_healthy = self.failure_count < 3
        self.last_used = time.time()

class RPCLoadBalancer:
    """Intelligent load balancer for multiple RPC endpoints"""
    
    def __init__(self):
        self.endpoints: List[RPCEndpoint] = []
        self.lock = Lock()
        self.current_index = 0
        self.setup_endpoints()
        
    def setup_endpoints(self):
        """Initialize all available RPC endpoints"""
        rpc_urls = Settings.RPC_URLS

        logger.info(f"Setting up RPC load balancer with {len(rpc_urls)} endpoints")
        
        def init_endpoint(url: str):
            try:
                w3 = Web3(
                    Web3.HTTPProvider(
                        url,
                        request_kwargs={
                            'headers': {
                                'Content-Type': 'application/json',
                                'Accept': 'application/json',
                                'User-Agent': 'Mozilla/5.0'
                            },
                            'timeout': 30
                        },
                    )
                )

                if w3.is_connected():
                    logger.info(f"✅ Connected to {url}")
                    return RPCEndpoint(url=url, w3=w3)
                logger.warning(f"❌ Failed to connect to {url}")
            except Exception as e:
                logger.warning(f"❌ Error setting up {url}: {e}")
            return None

        max_workers = max(1, min(8, len(rpc_urls)))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for endpoint in executor.map(init_endpoint, rpc_urls):
                if endpoint:
                    self.endpoints.append(endpoint)
        
        if not self.endpoints:
            raise ConnectionError("No RPC endpoints available!")
        
        logger.info(f"🚀 Load balancer ready with {len(self.endpoints)} healthy endpoints")
    
    def get_best_endpoint(self) -> RPCEndpoint:
        """Get the best available endpoint using intelligent selection"""
        with self.lock:
            now = time.time()
            for ep in self.endpoints:
                if ep.cooldown_until and ep.cooldown_until <= now and not ep.is_healthy:
                    ep.failure_count = 0
                    ep.is_healthy = True
            # Filter healthy, non-rate-limited endpoints
            healthy_endpoints = [
                ep for ep in self.endpoints
                if ep.is_healthy and not ep.is_rate_limited and ep.cooldown_until <= now
            ]
            
            if not healthy_endpoints:
                # All endpoints are struggling, use least recently used
                healthy_endpoints = sorted(
                    self.endpoints, 
                    key=lambda ep: ep.last_used
                )[:2]  # Take 2 least recently used
                logger.warning("⚠️  All endpoints throttled, using least recently used")
            
            # Prefer endpoints with faster response times
            best_endpoint = min(healthy_endpoints, key=lambda ep: ep.avg_response_time)
            
            return best_endpoint
    
    def get_round_robin_endpoint(self) -> RPCEndpoint:
        """Simple round-robin selection for maximum distribution"""
        with self.lock:
            now = time.time()
            for ep in self.endpoints:
                if ep.cooldown_until and ep.cooldown_until <= now and not ep.is_healthy:
                    ep.failure_count = 0
                    ep.is_healthy = True
            healthy_endpoints = [
                ep for ep in self.endpoints
                if ep.is_healthy and ep.cooldown_until <= now
            ]
            
            if not healthy_endpoints:
                healthy_endpoints = self.endpoints  # Use all if none healthy
            
            # Round robin through healthy endpoints
            endpoint = healthy_endpoints[self.current_index % len(healthy_endpoints)]
            self.current_index += 1
            
            return endpoint
    
    def execute_call(self, call_func, *args, **kwargs):
        """Execute a blockchain call with automatic endpoint selection and retry"""
        max_retries = len(self.endpoints)
        
        for attempt in range(max_retries):
            # Use round-robin for maximum load distribution
            endpoint = self.get_round_robin_endpoint()
            
            start_time = time.time()
            try:
                # Execute the call
                result = call_func(endpoint.w3, *args, **kwargs)
                
                # Record successful response
                response_time = time.time() - start_time
                endpoint.record_response(response_time, success=True)
                
                return result
                
            except Exception as e:
                response_time = time.time() - start_time
                endpoint.record_response(response_time, success=False)

                msg = str(e).lower()
                logger.debug(f"❌ Call failed on {endpoint.url}: {e}")

                if any(token in msg for token in ["429", "too many requests", "rate limit", "timeout"]):
                    # Back off this endpoint briefly
                    backoff = min(30, 5 * (endpoint.failure_count + 1))
                    endpoint.cooldown_until = time.time() + backoff
                    logger.warning(
                        f"Rate limit detected on {endpoint.url}; cooling down for {backoff}s"
                    )
                    time.sleep(min(3, backoff / 2))

                # Try next endpoint on failure
                if attempt == max_retries - 1:
                    logger.error(f"All endpoints failed after {max_retries} attempts")
                    raise e
        
        raise Exception("All RPC endpoints failed")
    
    def get_block_timestamp(self, block_num: int) -> Optional[int]:
        """Get block timestamp using load balanced RPC calls"""
        def _call(w3, block_num):
            block_data = w3.eth.get_block(block_num)
            return block_data['timestamp']
        
        return self.execute_call(_call, block_num)
    
    def get_amounts_out(self, router_contract_abi, router_address: str, amount_in: int, path: List[str]) -> List[int]:
        """Get amounts out using load balanced RPC calls"""
        def _call(w3, amount_in, path):
            router_contract = w3.eth.contract(address=router_address, abi=router_contract_abi)
            return router_contract.functions.getAmountsOut(amount_in, path).call()
        
        return self.execute_call(_call, amount_in, path)
    
    def get_amounts_out_at_block(self, router_contract_abi, router_address: str, amount_in: int, path: List[str], block_num: int) -> List[int]:
        """Get amounts out at specific block using load balanced RPC calls"""
        def _call(w3, amount_in, path, block_num):
            router_contract = w3.eth.contract(address=router_address, abi=router_contract_abi)
            return router_contract.functions.getAmountsOut(amount_in, path).call(block_identifier=block_num)
        
        return self.execute_call(_call, amount_in, path, block_num)

    def get_block_timestamps_batch(self, block_numbers: List[int]) -> Dict[int, Optional[int]]:
        """Fetch block timestamps for a batch of block numbers using a single RPC call when supported."""

        if not block_numbers:
            return {}

        def _call(w3, batch):
            provider = getattr(w3, 'provider', None)
            timestamps: Dict[int, Optional[int]] = {}

            if provider and hasattr(provider, 'make_batch_request'):
                payload = [
                    ('eth_getBlockByNumber', [hex(block), False])
                    for block in batch
                ]
                responses = provider.make_batch_request(payload)
                if not isinstance(responses, list):
                    raise ValueError("Invalid batch response for block timestamps")

                for idx, block in enumerate(batch):
                    ts = None
                    try:
                        entry = responses[idx]
                        if isinstance(entry, dict):
                            result = entry.get('result')
                            if result and 'timestamp' in result:
                                ts = int(result['timestamp'], 16)
                    except Exception:
                        ts = None
                    timestamps[block] = ts
                return timestamps

            # Fallback to sequential fetch on this endpoint
            for block in batch:
                try:
                    block_data = w3.eth.get_block(block)
                    timestamps[block] = block_data['timestamp']
                except Exception:
                    timestamps[block] = None
            return timestamps

        return self.execute_call(_call, block_numbers)
    
    def get_latest_block_number(self) -> int:
        """Get latest block number using load balanced RPC calls"""
        def _call(w3):
            return w3.eth.block_number
        
        return self.execute_call(_call)
    
    def get_health_stats(self) -> Dict:
        """Get health statistics for all endpoints"""
        stats = {}
        for i, endpoint in enumerate(self.endpoints):
            stats[f"endpoint_{i}"] = {
                'url': endpoint.url,
                'healthy': endpoint.is_healthy,
                'rate_limited': endpoint.is_rate_limited,
                'avg_response_time': endpoint.avg_response_time,
                'failure_count': endpoint.failure_count,
                'total_calls': len(endpoint.response_times)
            }
        return stats
    
    def log_performance_summary(self):
        """Log performance summary for all endpoints"""
        logger.info("🔍 RPC Load Balancer Performance Summary:")
        for i, endpoint in enumerate(self.endpoints):
            status = "🟢" if endpoint.is_healthy else "🔴"
            if endpoint.is_rate_limited:
                status += "🐌"
            
            logger.info(f"  {status} Endpoint {i+1}: {endpoint.url}")
            logger.info(f"    Avg Response: {endpoint.avg_response_time:.2f}s")
            logger.info(f"    Total Calls: {len(endpoint.response_times)}")
            logger.info(f"    Failures: {endpoint.failure_count}")
