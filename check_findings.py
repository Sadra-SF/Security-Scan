#!/usr/bin/env python
import os
import sys
import django

# Add the backend/src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'src'))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api_server.settings')
django.setup()

from findings.models import Finding

# Check findings
findings = Finding.objects.all()
print(f"Total findings: {findings.count()}")

for finding in findings:
    print(f"Finding: {finding.title} - {finding.severity}")
    print(f"  Location: {finding.locations}")
    print(f"  Description: {finding.description}")
    print(f"  Metadata: {finding.metadata}")
    print("---")