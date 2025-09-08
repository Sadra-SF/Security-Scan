from __future__ import annotations

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from scanners.network.nmap_adapter import NetworkNmapAdapter, _get_config_section
from scanners.base import ScanContext
from scanners.constants import Severity


class TestNetworkNmapAdapter:
    def test_adapter_properties(self):
        adapter = NetworkNmapAdapter()
        assert adapter.key == "network_nmap"
        assert adapter.name == "network.nmap"
        assert adapter.type == "network"
        assert adapter.display_name == "Network Nmap Scanner"

    def test_get_config_section(self):
        ctx = ScanContext(
            scan_run_id=1, asset_id=1, profile_id=1, started_at=datetime.now(timezone.utc),
            config={"nmap": {"targets": ["192.168.1.1"]}}
        )
        cfg = _get_config_section(ctx)
        assert cfg == {"targets": ["192.168.1.1"]}

        ctx = ScanContext(
            scan_run_id=1, asset_id=1, profile_id=1, started_at=datetime.now(timezone.utc),
            config={"network": {"nmap": {"scan_args": "-sV"}}}
        )
        cfg = _get_config_section(ctx)
        assert cfg == {"scan_args": "-sV"}

    def test_validate_config_valid(self):
        adapter = NetworkNmapAdapter()
        ctx = ScanContext(
            scan_run_id=1, asset_id=1, profile_id=1, started_at=datetime.now(timezone.utc),
            config={"nmap": {"timing": "T4"}}
        )
        # Should not raise
        adapter.validate_config(ctx)

    @patch('nmap.PortScanner')
    def test_run_with_targets(self, mock_nmap_class):
        mock_nm = MagicMock()
        mock_nmap_class.return_value = mock_nm

        # Mock host object
        mock_host = MagicMock()
        mock_host.all_protocols.return_value = ['tcp']
        mock_host.__getitem__.side_effect = lambda key: {
            'tcp': {
                80: {'state': 'open', 'name': 'http'},
                443: {'state': 'open', 'name': 'https'}
            },
            'osmatch': [{'name': 'Linux', 'accuracy': 95}]
        }[key]
        mock_host.__contains__.side_effect = lambda key: key in ['tcp', 'osmatch']

        # Mock scan results
        mock_nm.all_hosts.return_value = ['192.168.1.1']
        mock_nm.__getitem__.return_value = mock_host

        adapter = NetworkNmapAdapter()
        ctx = ScanContext(
            scan_run_id=1, asset_id=1, profile_id=1, started_at=datetime.now(timezone.utc),
            config={"nmap": {"targets": ["192.168.1.1"], "scan_args": "-sV"}}
        )

        findings = adapter.run(ctx)

        assert len(findings) == 3  # 2 open ports + 1 OS detection
        assert findings[0].title == "Open port 80/tcp (http)"
        assert findings[0].severity == Severity.MEDIUM
        assert findings[1].title == "Open port 443/tcp (https)"
        assert findings[1].severity == Severity.MEDIUM
        assert findings[2].title == "OS Detected: Linux"

    @patch('nmap.PortScanner')
    def test_run_no_targets_uses_asset(self, mock_nmap_class):
        mock_nm = MagicMock()
        mock_nmap_class.return_value = mock_nm
        mock_nm.all_hosts.return_value = ['10.0.0.1']

        adapter = NetworkNmapAdapter()
        ctx = ScanContext(
            scan_run_id=1, asset_id=1, profile_id=1, started_at=datetime.now(timezone.utc),
            config={"asset": {"type": "network", "url_or_cidr": "10.0.0.1"}}
        )

        findings = adapter.run(ctx)

        mock_nm.scan.assert_called_once_with(hosts='10.0.0.1', arguments='-sV -O')

    def test_run_no_targets_no_asset(self):
        adapter = NetworkNmapAdapter()
        ctx = ScanContext(
            scan_run_id=1, asset_id=1, profile_id=1, started_at=datetime.now(timezone.utc),
            config={}
        )

        findings = adapter.run(ctx)

        assert len(findings) == 1
        assert "invalid configuration" in findings[0].title

    @patch('nmap.PortScanner')
    def test_run_nmap_exception(self, mock_nmap_class):
        mock_nmap_class.side_effect = Exception("Nmap error")

        adapter = NetworkNmapAdapter()
        ctx = ScanContext(
            scan_run_id=1, asset_id=1, profile_id=1, started_at=datetime.now(timezone.utc),
            config={"nmap": {"targets": ["192.168.1.1"]}}
        )

        findings = adapter.run(ctx)

        assert len(findings) == 1
        assert findings[0].title == "Nmap scan error"
        assert findings[0].severity == Severity.MEDIUM

    def test_supports(self):
        adapter = NetworkNmapAdapter()

        # Should support network assets with network.nmap enabled
        assert adapter.supports({"type": "network"}, {"enabled_scanners": ["network.nmap"]})
        assert adapter.supports({"type": "host"}, {"enabled_scanners": ["network"]})

        # Should not support web assets
        assert not adapter.supports({"type": "web"}, {"enabled_scanners": ["network.nmap"]})

        # Should not support if not enabled
        assert not adapter.supports({"type": "network"}, {"enabled_scanners": ["static"]})