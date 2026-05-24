# RJ Auto Metadata
# Copyright (C) 2026 Riiicil
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

# src/api/api_key_checker.py
from src.api.provider_manager import (check_api_keys_status as provider_check_api_keys_status,get_default_provider,)

def check_api_keys_status(api_keys, model=None, provider=None, base_url_override=None):
    provider_name = provider or get_default_provider()
    return provider_check_api_keys_status(
        provider_name,
        api_keys,
        model=model,
        base_url_override=base_url_override,
    )