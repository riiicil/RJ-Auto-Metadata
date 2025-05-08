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
from src.utils.logging import log_message

# RPM (Requests Per Minute) data for Gemini models
# Based on README and gemini_api.py's GEMINI_MODELS list
MODEL_RPM_DATA = {
    "gemini-2.0-flash": 15,
    "gemini-2.0-flash-lite": 30,
    "gemini-1.5-flash-8b": 15,
    "gemini-1.5-flash": 15,
    "gemini-1.5-pro": 2,
    "gemini-2.5-flash-preview-04-17": 10,
    "gemini-2.5-pro-preview-03-25": 5,
    # Add other models here if needed, with their respective RPMs
}
DEFAULT_MODEL_RPM = 15 # Default RPM if a model is not in MODEL_RPM_DATA (e.g., gemini-1.5-flash)
DEFAULT_MODEL_CAPACITY = 8

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

    def get_potential_wait_time(self, tokens_to_consume=1):
        with self.lock:
            now = time.time()
            elapsed = now - self.last_update
            # Calculate current tokens without actually updating self.last_update or self.tokens
            current_tokens = min(self.capacity, self.tokens + (elapsed * self.fill_rate))

            if tokens_to_consume <= current_tokens:
                return 0  # No wait time needed
            else:
                # Calculate how many more tokens are needed
                needed_tokens = tokens_to_consume - current_tokens
                # Calculate time to generate these needed tokens
                wait_time = needed_tokens / self.fill_rate if self.fill_rate > 0 else float('inf') # Avoid division by zero
                return wait_time

# Factory function to create TokenBucket with model-specific fill_rate
def _create_model_specific_token_bucket(model_name: str):
    """
    Creates a TokenBucket for a given model_name with RPM-based fill_rate.
    """
    rpm = MODEL_RPM_DATA.get(model_name, DEFAULT_MODEL_RPM)
    # Convert RPM to fill_rate in tokens per second
    # Example: 15 RPM = 15 requests / 60 seconds = 0.25 tokens/second
    fill_rate_per_second = rpm / 60.0
    
    # Capacity can also be made dynamic per model if needed in the future
    capacity = DEFAULT_MODEL_CAPACITY 
    
    log_message(f"[RateLimiterDebug] Creating TokenBucket for model: {model_name}, RPM: {rpm}, Fill Rate: {fill_rate_per_second:.4f} tokens/sec, Capacity: {capacity}", "debug")
    return TokenBucket(capacity, fill_rate_per_second)

# Global instances of rate limiters
# MODEL_RATE_LIMITERS = defaultdict(_create_model_specific_token_bucket) # Old incorrect way

class ModelRateLimiterDict(defaultdict):
    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        # 'key' here is the model_name
        self[key] = self.default_factory(key) # Call factory with the key (model_name)
        return self[key]

MODEL_RATE_LIMITERS = ModelRateLimiterDict(_create_model_specific_token_bucket)
API_RATE_LIMITERS = defaultdict(lambda: TokenBucket(10, 1/3.0))