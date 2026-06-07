# RJ Auto Metadata
# Copyright (C) 2026 Riiicil
#
# Unit tests for iLabs registration and space preservation.

import sys
import threading
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.api import provider_manager, ilabs_api


def test_ilabs_is_registered():
    """Verify that iLabs is in the list of providers."""
    providers = provider_manager.list_providers()
    assert provider_manager.PROVIDER_ILABS in providers
    assert "iLabs" in providers
    print("PASS: test_ilabs_is_registered")


def test_keyword_spaces_preserved():
    """Verify that multi-word keywords containing spaces are NOT stripped of spaces.

    This tests the space-preservation fix in provider_manager._fill_keywords_if_short().
    """
    captured_data = {
        "title": "A Beautiful Railway Station",
        "description": "A steam locomotive arrives at the main railway station.",
        "tags": ["railway station", "steam locomotive", "train", "kai access line"],
        "adobe_stock_category": "1",
        "shutterstock_category": "Transportation",
    }

    # We mock get_ilabs_metadata to return our test metadata
    original_get = ilabs_api.get_ilabs_metadata
    ilabs_api.get_ilabs_metadata = lambda *args, **kwargs: captured_data

    try:
        # Call provider_manager.get_metadata which triggers _fill_keywords_if_short() internally
        result = provider_manager.get_metadata(
            provider=provider_manager.PROVIDER_ILABS,
            image_path="C:/fake/image.jpg",
            api_key="fake-key",
            stop_event=threading.Event(),
            selected_model="gpt-4o-mini",
            keyword_count="49",
        )

        assert isinstance(result, dict), "Result should be a dictionary"
        assert "error" not in result, f"Result contains error: {result}"
        
        tags = result.get("tags", [])
        
        # Verify that spaces are preserved and not stripped to "railwaystation" or "steamlocomotive"
        assert "railway station" in tags, f"'railway station' not in tags: {tags}"
        assert "steam locomotive" in tags, f"'steam locomotive' not in tags: {tags}"
        assert "kai access line" in tags, f"'kai access line' not in tags: {tags}"
        
        # Verify no tag has spaces removed (which would be the bug)
        assert "railwaystation" not in tags
        assert "steamlocomotive" not in tags
        assert "kaiaccessline" not in tags

        print("PASS: test_keyword_spaces_preserved")

    finally:
        ilabs_api.get_ilabs_metadata = original_get


def main():
    test_ilabs_is_registered()
    test_keyword_spaces_preserved()
    print("\nAll iLabs and space-preservation tests passed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
