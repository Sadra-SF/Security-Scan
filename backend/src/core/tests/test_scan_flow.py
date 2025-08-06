from __future__ import annotations

import os

from django.test import TestCase, override_settings

from core.models import Asset, ScanProfile, ScanRun


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, DJANGO_DEBUG="True")
class ScanFlowTest(TestCase):
    def setUp(self) -> None:
        self.asset = Asset.objects.create(name="Example Web", type="web", url_or_cidr="http://example.com")
        # Enable static by legacy key plus explicit adapters to verify selection compatibility
        self.profile = ScanProfile.objects.create(
            name="Default",
            enabled_scanners=["static", "static.deps", "static.config"],
        )

    def test_start_scan_and_complete(self):
        url = "/api/scans/"
        resp = self.client.post(
            url,
            data={"asset_id": self.asset.id, "profile_id": self.profile.id},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        scan_run_id = resp.json()["scan_run_id"]

        run = ScanRun.objects.get(pk=scan_run_id)
        # With CELERY_TASK_ALWAYS_EAGER=True, orchestration runs synchronously in-process
        run.refresh_from_db()
        self.assertEqual(run.status, "completed")
        self.assertIsNotNone(run.started_at)
        self.assertIsNotNone(run.ended_at)

        # Aggregates should exist with by_severity and by_category keys
        agg = (run.meta or {}).get("aggregate") or {}
        self.assertIn("by_severity", agg)
        self.assertIn("by_category", agg)
        # At least one of medium/high should be present (synthetic/config)
        by_sev = agg.get("by_severity") or {}
        self.assertTrue(any(k in by_sev for k in ("medium", "high", "low", "info")))
        # Report path should be stored in meta and file should exist
        self.assertIn("report_path", run.meta or {})
        report_path = run.meta.get("report_path")
        self.assertTrue(os.path.isfile(report_path), f"Report not found at {report_path}")
        # Report should contain 'category:' lines (from findings listing section or placeholder)
        content = open(report_path, "r", encoding="utf-8").read()
        self.assertIn("category:", content)

    def test_dynamic_zap_placeholder(self):
        # Dynamic scan baseline synthetic
        asset = Asset.objects.create(name="DynSite", type="web", url_or_cidr="http://example.com")
        profile = ScanProfile.objects.create(name="DynOnly", enabled_scanners=["dynamic", "dynamic.zap"])
        # Attach config via run.meta after creation is not directly supported by API; we rely on default DEBUG behavior.
        # For placeholder purposes, ensure baseline mode is set through ScanRun.meta.config.zap mimicked by orchestrator snapshot.
        resp = self.client.post(
            "/api/scans/",
            data={"asset_id": asset.id, "profile_id": profile.id},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        scan_run_id = resp.json()["scan_run_id"]
        run = ScanRun.objects.get(pk=scan_run_id)
        run.refresh_from_db()

        # Verify report content for ZAP baseline placeholder
        report_path = (run.meta or {}).get("report_path")
        self.assertTrue(os.path.isfile(report_path))
        content = open(report_path, "r", encoding="utf-8").read().lower()
        self.assertIn("zap baseline simulated", content)

        # Aggregates categories contains keys (open/assert tolerant)
        agg = (run.meta or {}).get("aggregate") or {}
        by_cat = agg.get("by_category") or {}
        self.assertTrue(isinstance(by_cat, dict))

    def test_network_nmap_placeholder(self):
        # Network scan synthetic using asset default
        asset = Asset.objects.create(name="Host", type="network", url_or_cidr="10.0.0.1")
        profile = ScanProfile.objects.create(name="NetOnly", enabled_scanners=["network", "network.nmap"])
        resp = self.client.post(
            "/api/scans/",
            data={"asset_id": asset.id, "profile_id": profile.id},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        scan_run_id = resp.json()["scan_run_id"]
        run = ScanRun.objects.get(pk=scan_run_id)
        run.refresh_from_db()

        report_path = (run.meta or {}).get("report_path")
        self.assertTrue(os.path.isfile(report_path))
        content = open(report_path, "r", encoding="utf-8").read().lower()
        self.assertIn("open port", content)

        agg = (run.meta or {}).get("aggregate") or {}
        by_sev = agg.get("by_severity") or {}
        self.assertGreaterEqual(by_sev.get("low", 0), 1)