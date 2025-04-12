# src/api/rate_limiter.py
import time
import threading
from collections import defaultdict

class TokenBucket:
    def __init__(self, capacity, fill_rate):
        self.capacity = capacity
        self.fill_rate = fill_rate
        self.tokens = capacity
        self.last_update = time.time()
        self.lock = threading.Lock()
    
    def consume(self, tokens=1):
        with self.lock:
            now = time.time()
            elapsed = now - self.last_update
            new_tokens = elapsed * self.fill_rate
            self.tokens = min(self.capacity, self.tokens + new_tokens)
            self.last_update = now
            if tokens <= self.tokens:
                self.tokens -= tokens
                return 0 
            else:
                wait_time = (tokens - self.tokens) / self.fill_rate
                return wait_time

# Global instances of rate limiters
MODEL_RATE_LIMITERS = defaultdict(lambda: TokenBucket(8, 1/3.0))
API_RATE_LIMITERS = defaultdict(lambda: TokenBucket(10, 1/3.0))