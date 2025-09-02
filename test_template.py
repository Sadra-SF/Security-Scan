#!/usr/bin/env python
import os
import sys
import django

# Add the backend/src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'src'))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api_server.settings')
django.setup()

from django.template.loader import render_to_string

# Test rendering the template
try:
    html = render_to_string('html/base.html', {
        'report': type('MockReport', (), {'title': 'Test Report', 'version': '1.0'})(),
        'project': type('MockProject', (), {'name': 'Test Project'})(),
        'generated_at': django.utils.timezone.now(),
    })
    print("Template rendered successfully!")
    print(f"HTML length: {len(html)}")
except Exception as e:
    print(f"Template rendering failed: {e}")