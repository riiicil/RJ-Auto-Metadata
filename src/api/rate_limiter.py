# RJ Auto Metadata
# Copyright (C) 2025 Riiicil
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

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