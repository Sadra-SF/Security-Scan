from __future__ import annotations

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from scanners.dynamic.zap_adapter import DynamicZapAdapter, _get_config_section
from scanners.base import ScanContext
from scanners.constants import Severity


class TestDynamicZapAdapter:
    def test_adapter_properties(self):
        adapter = DynamicZapAdapter()
        assert adapter.key == "dynamic_zap"
        assert adapter.name == "dynamic.zap"
        assert adapter.type == "dynamic"
        assert adapter.display_name == "Dynamic ZAP Scanner"

    def test_get_config_section(self):
        ctx = ScanContext(
            scan_run_id=1, asset_id=1, profile_id=1, started_at=datetime.now(timezone.utc),
            config={"zap": {"url": "http://example.com"}}
        )
        cfg = _get_config_section(ctx)
        assert cfg == {"url": "http://example.com"}

        ctx = ScanContext(
            scan_run_id=1, asset_id=1, profile_id=1, started_at=datetime.now(timezone.utc),
            config={"dynamic": {"zap": {"mode": "baseline"}}}
        )
        cfg = _get_config_section(ctx)
        assert cfg == {"mode": "baseline"}

    def test_validate_config_valid(self):
        adapter = DynamicZapAdapter()
        ctx = ScanContext(
            scan_run_id=1, asset_id=1, profile_id=1, started_at=datetime.now(timezone.utc),
            config={"zap": {"mode": "baseline"}}
        )
        # Should not raise
        adapter.validate_config(ctx)

    @patch('scanners.dynamic.zap_adapter.ZAPv2')
    @patch('scanners.dynamic.zap_adapter.subprocess.Popen')
    def test_run_baseline_mode(self, mock_popen, mock_zap_class):
        mock_zap = Mock()
        mock_zap_class.return_value = mock_zap
        mock_zap.core.version.return_value = "2.10.0"
        mock_zap.ascan.status.return_value = "100"
        mock_zap.core.alerts.return_value = [
            {
                "alert": "XSS",
                "risk": "High",
                "description": "Cross-site scripting",
                "url": "http://example.com",
                "evidence": "test",
                "solution": "Sanitize input",
                "pluginId": "40012"
            }
        ]

        adapter = DynamicZapAdapter()
        ctx = ScanContext(
            scan_run_id=1, asset_id=1, profile_id=1, started_at=datetime.now(timezone.utc),
            config={"zap": {"url": "http://example.com", "mode": "baseline"}}
        )

        findings = adapter.run(ctx)

        assert len(findings) == 1
        assert findings[0].title == "ZAP: XSS"
        assert findings[0].severity == Severity.HIGH
        assert findings[0].description == "Cross-site scripting"

    @patch('scanners.dynamic.zap_adapter.ZAPv2')
    def test_run_no_url(self, mock_zap_class):
        adapter = DynamicZapAdapter()
        ctx = ScanContext(
            scan_run_id=1, asset_id=1, profile_id=1, started_at=datetime.now(timezone.utc),
            config={"zap": {}}
        )

        findings = adapter.run(ctx)

        assert len(findings) == 1
        assert "invalid configuration" in findings[0].title

    @patch('scanners.dynamic.zap_adapter.ZAPv2')
    @patch('scanners.dynamic.zap_adapter.subprocess.Popen')
    def test_run_zap_exception(self, mock_popen, mock_zap_class):
        mock_zap_class.side_effect = Exception("ZAP error")

        adapter = DynamicZapAdapter()
        ctx = ScanContext(
            scan_run_id=1, asset_id=1, profile_id=1, started_at=datetime.now(timezone.utc),
            config={"zap": {"url": "http://example.com"}}
        )

        findings = adapter.run(ctx)

        assert len(findings) == 1
        assert findings[0].title == "ZAP scan error"
        assert findings[0].severity == Severity.MEDIUM

    @patch('scanners.dynamic.zap_adapter.ZAPv2')
    @patch('scanners.dynamic.zap_adapter.subprocess.Popen')
    def test_run_unknown_mode(self, mock_popen, mock_zap_class):
        mock_zap = Mock()
        mock_zap_class.return_value = mock_zap
        mock_zap.core.version.return_value = "2.10.0"

        adapter = DynamicZapAdapter()
        ctx = ScanContext(
            scan_run_id=1, asset_id=1, profile_id=1, started_at=datetime.now(timezone.utc),
            config={"zap": {"url": "http://example.com", "mode": "unknown"}}
        )

        findings = adapter.run(ctx)

        assert len(findings) == 1
        assert findings[0].title == "Unknown ZAP scan mode"

    def test_supports(self):
        adapter = DynamicZapAdapter()

        # Should support web assets with dynamic.zap enabled
        assert adapter.supports({"type": "web"}, {"enabled_scanners": ["dynamic.zap"]})
        assert adapter.supports({"type": "http"}, {"enabled_scanners": ["dynamic"]})

        # Should not support network assets
        assert not adapter.supports({"type": "network"}, {"enabled_scanners": ["dynamic.zap"]})

        # Should not support if not enabled
        assert not adapter.supports({"type": "web"}, {"enabled_scanners": ["static"]})