import pytest
from url_classifier_exceptions_manager.__main__ import (
    parse_rs_record,
)

def test_parse_rs_record():
    """Test parsing of RemoteSettings records with old bugId field."""
    test_record = {
        "id": "2a50e5fa-4762-4a3b-a5d0-53a7e9bbe91a",
        "bugId": "123456",
        "urlPattern": "*://example.com/*",
        "classifierFeatures": ["tracking-protection"],
        "topLevelUrlPattern": "*://example.net/*",
        "isPrivateBrowsingOnly": True,
        "filterContentBlockingCategories": ["standard"]
    }

    parsed = parse_rs_record(test_record)
    
    assert parsed["id"] == "2a50e5fa-4762-4a3b-a5d0-53a7e9bbe91a"
    assert parsed["bugIds"] == ["123456"]
    assert parsed["urlPattern"] == "*://example.com/*"
    assert parsed["classifierFeatures"] == ["tracking-protection"]
    assert parsed["topLevelUrlPattern"] == "*://example.net/*"
    assert parsed["isPrivateBrowsingOnly"] is True
    assert parsed["filterContentBlockingCategories"] == ["standard"]

def test_parse_rs_record_bugIds():
    """Test parsing of RemoteSettings records with new bugIds field."""
    test_record = {
        "id": "2a50e5fa-4762-4a3b-a5d0-53a7e9bbe91a",
        "bugIds": ["123456", "654321"],
        "urlPattern": "*://example.com/*",
        "classifierFeatures": ["tracking-protection"]
    }
    parsed = parse_rs_record(test_record)
    assert parsed["id"] == "2a50e5fa-4762-4a3b-a5d0-53a7e9bbe91a"
    assert parsed["bugIds"] == ["123456", "654321"]
    assert parsed["urlPattern"] ==  "*://example.com/*"
    assert parsed["classifierFeatures"] == ["tracking-protection"]

def test_parse_rs_record_minimal():
    """Test parsing of RemoteSettings records with only required fields (old format)."""
    test_record = {
        "id": "2a50e5fa-4762-4a3b-a5d0-53a7e9bbe91a",
        "bugId": "123456",
        "urlPattern": "*://example.com/*",
        "classifierFeatures": ["tracking-protection"]
    }

    parsed = parse_rs_record(test_record)
    
    assert parsed["id"] == "2a50e5fa-4762-4a3b-a5d0-53a7e9bbe91a"
    assert parsed["bugIds"] == ["123456"]
    assert parsed["urlPattern"] ==  "*://example.com/*"
    assert parsed["classifierFeatures"] == ["tracking-protection"]
    assert "topLevelUrlPattern" not in parsed
    assert "isPrivateBrowsingOnly" not in parsed
    assert "filterContentBlockingCategories" not in parsed 