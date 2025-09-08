"""
Evidence retention policy management.
"""
import logging
from datetime import timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass

from django.utils import timezone
from django.db.models import Q

from .models import Evidence

logger = logging.getLogger(__name__)


@dataclass
class RetentionRule:
    """A single retention rule."""
    name: str
    description: str
    condition: Callable[[Evidence], bool]
    action: str  # 'delete', 'archive', 'compress'
    priority: int = 0


@dataclass
class RetentionPolicy:
    """A collection of retention rules."""
    name: str
    description: str
    rules: List[RetentionRule]
    enabled: bool = True


class RetentionManager:
    """Manages evidence retention policies."""

    def __init__(self):
        self.policies = self._load_default_policies()

    def _load_default_policies(self) -> List[RetentionPolicy]:
        """Load default retention policies."""
        return [
            RetentionPolicy(
                name="standard_cleanup",
                description="Standard cleanup policy for old evidence",
                rules=[
                    RetentionRule(
                        name="delete_old_screenshots",
                        description="Delete screenshots older than 90 days",
                        condition=lambda e: e.kind == 'screenshot' and
                                          (timezone.now() - e.created_at).days > 90,
                        action="delete",
                        priority=1
                    ),
                    RetentionRule(
                        name="archive_old_logs",
                        description="Archive logs older than 180 days",
                        condition=lambda e: e.kind == 'log' and
                                          (timezone.now() - e.created_at).days > 180,
                        action="archive",
                        priority=2
                    ),
                    RetentionRule(
                        name="delete_large_files",
                        description="Delete files larger than 100MB older than 30 days",
                        condition=lambda e: e.size and e.size > 100 * 1024 * 1024 and
                                          (timezone.now() - e.created_at).days > 30,
                        action="delete",
                        priority=3
                    ),
                    RetentionRule(
                        name="compress_old_artifacts",
                        description="Compress artifacts older than 60 days",
                        condition=lambda e: e.kind == 'artifact' and
                                          (timezone.now() - e.created_at).days > 60,
                        action="compress",
                        priority=4
                    )
                ]
            ),
            RetentionPolicy(
