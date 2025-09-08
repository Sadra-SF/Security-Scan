#!/usr/bin/env python3
"""
Security Scanner Demo Script

This script automates the key demo workflow for the security scanner application.
It includes backend/frontend verification, sample data setup, target creation,
scan execution, findings display, and key feature demonstrations.

Usage:
    python demo_script.py --full          # Run complete demo
    python demo_script.py --verify        # Verify services
    python demo_script.py --setup         # Setup sample data
    python demo_script.py --target        # Create target
    python demo_script.py --scan          # Execute scan
    python demo_script.py --findings      # Display findings
    python demo_script.py --demo          # Demonstrate features
"""

import os
import sys
import time
import argparse
import requests
from requests.exceptions import RequestException
import django
from django.conf import settings

# Add backend/src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'src'))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api_server.settings')
django.setup()

from projects.models import Organization, Project
from targets.models import Target
from scans.models import Scan
from findings.models import Finding
from scans.tasks import start_scan
from scanners.registry import list_plugins_by_type

class DemoScript:
    def __init__(self):
        self.backend_url = 'http://localhost:8000'
        self.frontend_url = 'http://localhost:3000'
        self.org = None
        self.project = None
        self.target = None
        self.scan = None

    def print_step(self, step, message):
        print(f"\n[STEP {step}] {message}")
        print("-" * 50)

    def print_success(self, message):
        print(f"✅ {message}")

    def print_error(self, message):
        print(f"❌ {message}")

    def print_info(self, message):
        print(f"ℹ️  {message}")

    def verify_services(self):
        """Verify backend and frontend are running"""
        self.print_step(1, "Verifying Backend and Frontend Services")

        # Check backend
        try:
            response = requests.get(f"{self.backend_url}/health/", timeout=5)
            if response.status_code == 200:
                self.print_success("Backend service is running")
            else:
                self.print_error(f"Backend returned status {response.status_code}")
                return False
        except RequestException as e:
            self.print_error(f"Cannot connect to backend: {e}")
            return False

        # Check frontend
        try:
            response = requests.get(self.frontend_url, timeout=5)
            if response.status_code == 200:
                self.print_success("Frontend service is running")
            else:
                self.print_error(f"Frontend returned status {response.status_code}")
                return False
        except RequestException as e:
            self.print_error(f"Cannot connect to frontend: {e}")
            return False

        return True

    def setup_sample_data(self):
        """Setup sample organization, project, and target"""
        self.print_step(2, "Setting up Sample Data")

        try:
            # Create organization
            self.org, created = Organization.objects.get_or_create(
                name='Demo Organization',
                defaults={'slug': 'demo-org'}
            )
            self.print_success(f"Organization: {self.org.name} ({'created' if created else 'exists'})")

            # Create project
            self.project, created = Project.objects.get_or_create(
                organization=self.org,
                name='Demo Project',
                defaults={'slug': 'demo-project', 'description': 'Demo project for security scanning'}
            )
            self.print_success(f"Project: {self.project.name} ({'created' if created else 'exists'})")

            return True
        except Exception as e:
            self.print_error(f"Failed to setup sample data: {e}")
            return False

    def create_target(self):
        """Create a demo target"""
        self.print_step(3, "Creating Demo Target")

        if not self.project:
            self.print_error("Project not available. Run setup first.")
            return False

        try:
            self.target, created = Target.objects.get_or_create(
                project=self.project,
                name='Demo Web Application',
                defaults={
                    'slug': 'demo-web-app',
                    'type': 'web',
                    'address': 'https://httpbin.org',
                    'settings': {'demo_mode': True}
                }
            )
            self.print_success(f"Target: {self.target.name} ({'created' if created else 'exists'})")
            self.print_info(f"Target URL: {self.target.address}")

            return True
        except Exception as e:
            self.print_error(f"Failed to create target: {e}")
            return False

    def execute_scan(self):
        """Execute a security scan"""
        self.print_step(4, "Executing Security Scan")

        if not self.target:
            self.print_error("Target not available. Run target creation first.")
            return False

        try:
            # Get available static plugins
            static_plugins = list_plugins_by_type('static')
            self.print_info(f"Available static plugins: {[p.key for p in static_plugins]}")

            # Create scan
            self.scan = Scan.objects.create(
                target=self.target,
                scanner='static_test',
                type='manual',
                config={'demo_mode': True}
            )
            self.print_success(f"Created scan: {self.scan.id}")

            # Run scan
            self.print_info("Starting scan execution...")
            start_scan(str(self.scan.id))

            # Wait for scan to complete (simple polling)
            max_attempts = 30
            attempt = 0
            while attempt < max_attempts:
                self.scan.refresh_from_db()
                if self.scan.status in ['completed', 'failed']:
                    break
                time.sleep(2)
                attempt += 1
                self.print_info(f"Scan status: {self.scan.status} (attempt {attempt}/{max_attempts})")

            if self.scan.status == 'completed':
                self.print_success("Scan completed successfully")
            else:
                self.print_error(f"Scan finished with status: {self.scan.status}")

            return True
        except Exception as e:
            self.print_error(f"Failed to execute scan: {e}")
            return False

    def display_findings(self):
        """Display scan findings"""
        self.print_step(5, "Displaying Scan Findings")

        if not self.scan:
            self.print_error("Scan not available. Run scan execution first.")
            return False

        try:
            findings = Finding.objects.filter(scan=self.scan)
            count = findings.count()
            self.print_info(f"Found {count} findings")

            if count > 0:
                for finding in findings[:5]:  # Show first 5
                    print(f"  - {finding.title} (Severity: {finding.severity}, Status: {finding.status})")
                if count > 5:
                    self.print_info(f"... and {count - 5} more findings")
            else:
                self.print_info("No findings found")

            return True
        except Exception as e:
            self.print_error(f"Failed to display findings: {e}")
            return False

    def demonstrate_features(self):
        """Demonstrate key application features"""
        self.print_step(6, "Demonstrating Key Features")

        try:
            # Show dashboard summary
            self.print_info("Dashboard Summary:")
            findings = Finding.objects.all()
            open_findings = findings.filter(status='open')
            severity_counts = {}
            for finding in open_findings:
                severity_counts[finding.severity] = severity_counts.get(finding.severity, 0) + 1

            for severity, count in severity_counts.items():
                print(f"  - {severity.capitalize()}: {count} open findings")

            # Show recent scans
            recent_scans = Scan.objects.order_by('-created_at')[:3]
            self.print_info("Recent Scans:")
            for scan in recent_scans:
                print(f"  - {scan.target.name}: {scan.status} ({scan.created_at})")

            # Show targets
            targets = Target.objects.all()
            self.print_info(f"Total targets: {targets.count()}")

            self.print_success("Feature demonstration completed")
            return True
        except Exception as e:
            self.print_error(f"Failed to demonstrate features: {e}")
            return False

    def run_full_demo(self):
        """Run the complete demo workflow"""
        print("🚀 Starting Security Scanner Demo")
        print("=" * 50)

        steps = [
            self.verify_services,
            self.setup_sample_data,
            self.create_target,
            self.execute_scan,
            self.display_findings,
            self.demonstrate_features
        ]

        for step in steps:
            if not step():
                self.print_error("Demo stopped due to error")
                return False

        print("\n" + "=" * 50)
        self.print_success("Demo completed successfully!")
        self.print_info("You can now explore the web interface at http://localhost:3000")
        return True

def main():
    parser = argparse.ArgumentParser(description='Security Scanner Demo Script')
    parser.add_argument('--full', action='store_true', help='Run complete demo')
    parser.add_argument('--verify', action='store_true', help='Verify services')
    parser.add_argument('--setup', action='store_true', help='Setup sample data')
    parser.add_argument('--target', action='store_true', help='Create target')
    parser.add_argument('--scan', action='store_true', help='Execute scan')
    parser.add_argument('--findings', action='store_true', help='Display findings')
    parser.add_argument('--demo', action='store_true', help='Demonstrate features')

    args = parser.parse_args()

    demo = DemoScript()

    if args.full:
        demo.run_full_demo()
    elif args.verify:
        demo.verify_services()
    elif args.setup:
        demo.setup_sample_data()
    elif args.target:
        demo.create_target()
    elif args.scan:
        demo.execute_scan()
    elif args.findings:
        demo.display_findings()
    elif args.demo:
        demo.demonstrate_features()
    else:
        parser.print_help()

if __name__ == '__main__':
    main()