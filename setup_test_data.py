#!/usr/bin/env python
import os
import sys
import django

# Add the backend/src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'src'))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api_server.settings')
django.setup()

from projects.models import Organization, Project
from targets.models import Target

# Create test organization
org, created = Organization.objects.get_or_create(
    name='Test Organization',
    defaults={'slug': 'test-org'}
)
print(f"Organization: {org} (created: {created})")

# Create test project
project, created = Project.objects.get_or_create(
    organization=org,
    name='Test Project',
    defaults={'slug': 'test-project', 'description': 'Test project for security scanning'}
)
print(f"Project: {project} (created: {created})")

# Create test target
target, created = Target.objects.get_or_create(
    project=project,
    name='Test Web App',
    defaults={
        'slug': 'test-web-app',
        'type': 'web',
        'address': 'http://example.com',
        'settings': {'test_mode': True}
    }
)
print(f"Target: {target} (created: {created})")

print("Test data setup complete!")