#!/usr/bin/env python
import os
import sys
import django

# Add the backend/src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'src'))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api_server.settings')
django.setup()

from scanners.static.config_adapter import _mk_finding

# Test creating a FindingRecord
record = _mk_finding(
    plugin_key="static_config",
    asset_id=123,
    category="test_category",
    title="Test finding",
    key="test_key"
)

print(f"Record: {record}")
print(f"Plugin key: {record.plugin_key}")
print(f"Category: {record.category}")
print(f"Title: {record.title}")
print(f"Has plugin_key attr: {hasattr(record, 'plugin_key')}")
print(f"Dir: {[attr for attr in dir(record) if not attr.startswith('_')]}")