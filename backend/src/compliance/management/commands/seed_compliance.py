import json
from pathlib import Path
from django.core.management.base import BaseCommand
from compliance.models import ComplianceTag


class Command(BaseCommand):
    help = "Seed compliance tags (OWASP Top Ten O1–O10). Reads compliance/data/owasp.json if present; otherwise seeds defaults. Idempotent."

    def handle(self, *args, **options):
        base_dir = Path(__file__).resolve().parents[3]  # points to backend/src
        data_path = base_dir / "compliance" / "data" / "owasp.json"

        if data_path.exists():
            self.stdout.write(f"Loading OWASP tags from: {data_path}")
            try:
                with data_path.open("r", encoding="utf-8") as f:
                    items = json.load(f)
                    if not isinstance(items, list):
                        raise ValueError("owasp.json must be a list of objects")
            except Exception as e:
                self.stderr.write(f"Failed to read {data_path}: {e}")
                return
        else:
            self.stdout.write("No owasp.json found; seeding default OWASP Top Ten O1–O10")
            items = [
                {"slug": "O1", "title": "Broken Access Control", "description": "", "category": "OWASP"},
                {"slug": "O2", "title": "Cryptographic Failures", "description": "", "category": "OWASP"},
                {"slug": "O3", "title": "Injection", "description": "", "category": "OWASP"},
                {"slug": "O4", "title": "Insecure Design", "description": "", "category": "OWASP"},
                {"slug": "O5", "title": "Security Misconfiguration", "description": "", "category": "OWASP"},
                {"slug": "O6", "title": "Vulnerable and Outdated Components", "description": "", "category": "OWASP"},
                {"slug": "O7", "title": "Identification and Authentication Failures", "description": "", "category": "OWASP"},
                {"slug": "O8", "title": "Software and Data Integrity Failures", "description": "", "category": "OWASP"},
                {"slug": "O9", "title": "Security Logging and Monitoring Failures", "description": "", "category": "OWASP"},
                {"slug": "O10", "title": "Server-Side Request Forgery", "description": "", "category": "OWASP"},
            ]

        created = 0
        updated = 0
        for item in items:
            slug = str(item.get("slug")).strip()
            title = item.get("title", "").strip()
            description = item.get("description", "")
            category = item.get("category", "OWASP")
            metadata = item.get("metadata", {})

            if not slug or not title:
                self.stderr.write(f"Skipping invalid item (missing slug or title): {item}")
                continue

            obj, was_created = ComplianceTag.objects.update_or_create(
                slug=slug,
                defaults={
                    "title": title,
                    "description": description,
                    "category": category,
                    "metadata": metadata,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"Compliance seed complete. Created: {created}, Updated: {updated}"))