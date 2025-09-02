#!/usr/bin/env python
import os
import sys
import django

# Add the backend/src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'src'))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api_server.settings')
django.setup()

from scanners.types import FindingRecord

# Test creating a FindingRecord
record = FindingRecord(
    "static_deps",
    "dependency_vuln",
    "Test vulnerability",
    "Test description",
    "high",
    "test:location",
    [],
    {"test": "metadata"},
    []
)

print(f"Record: {record}")
print(f"Plugin key: {record.plugin_key}")
print(f"Category: {record.category}")
print(f"Title: {record.title}")
print(f"Has plugin_key attr: {hasattr(record, 'plugin_key')}")
print(f"Dir: {[attr for attr in dir(record) if not attr.startswith('_')]}")