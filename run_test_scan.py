#!/usr/bin/env python
import os
import sys
import django

# Add the backend/src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'src'))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api_server.settings')
django.setup()

from scans.models import Scan
from targets.models import Target
from scans.tasks import run_static_scan
from scanners.registry import list_plugins_by_type

# Get the test target
try:
    target = Target.objects.get(slug='test-web-app')
    print(f"Found target: {target}")
except Target.DoesNotExist:
    print("Target not found!")
    sys.exit(1)

# Create a scan
scan = Scan.objects.create(
    target=target,
    scanner='static_test',
    type='manual',
    config={'test_mode': True}
)
print(f"Created scan: {scan}")

# Get static plugins
static_plugins = list_plugins_by_type('static')
print(f"Available static plugins: {[p.key for p in static_plugins]}")

# Run static scans
for plugin in static_plugins:
    print(f"Running static scan with plugin: {plugin.key}")
    try:
        result = run_static_scan(str(scan.id), plugin.key)
        print(f"Plugin {plugin.key} result: {result}")
    except Exception as e:
        print(f"Error running plugin {plugin.key}: {e}")

print("Static scans completed!")