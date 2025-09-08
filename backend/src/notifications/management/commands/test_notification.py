from django.core.management.base import BaseCommand
from django.conf import settings
from notifications.tasks import _dispatch_channel, _build_context, _match_rules
from notifications.models import NotificationChannel, NotificationRule
from scans.models import Scan
from django.utils import timezone


class Command(BaseCommand):
    help = 'Test notification system with synchronous dispatch'

    def add_arguments(self, parser):
        parser.add_argument(
            '--scan-id',
            type=str,
            help='Scan ID to use for notification test',
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Test email address',
        )
        parser.add_argument(
            '--channel-type',
            type=str,
            default='email',
            choices=['email', 'slack', 'teams', 'webhook'],
            help='Notification channel type',
        )

    def handle(self, *args, **options):
        self.stdout.write('Testing notification system...')

        # Get or create a test scan
        scan_id = options.get('scan_id')
        if scan_id:
            try:
                scan = Scan.objects.get(id=scan_id)
            except Scan.DoesNotExist:
                self.stderr.write(f'Scan with ID {scan_id} not found')
                return
        else:
            # Create a mock scan for testing
            from targets.models import Target
            from projects.models import Project, Organization

            # Get first available target or create one
            try:
                target = Target.objects.first()
                if not target:
                    # Create test data
                    org, _ = Organization.objects.get_or_create(
                        name='Test Organization',
                        defaults={'slug': 'test-org'}
                    )
                    project, _ = Project.objects.get_or_create(
                        name='Test Project',
                        organization=org,
                        defaults={'slug': 'test-project'}
                    )
                    target, _ = Target.objects.get_or_create(
                        name='Test Target',
                        project=project,
                        defaults={
                            'target_url': 'https://example.com',
                            'target_type': 'web'
                        }
                    )
            except Exception as e:
                self.stderr.write(f'Error creating test data: {e}')
                return

            # Create a mock scan
            scan = Scan.objects.create(
                target=target,
                scanner='test',
                status='completed',
                started_at=timezone.now(),
                finished_at=timezone.now(),
                stats={
                    'total': 5,
                    'by_severity': {'high': 2, 'medium': 1, 'low': 2},
                    'by_category': {'injection': 1, 'xss': 2, 'config': 2}
                }
            )
            self.stdout.write(f'Created test scan: {scan.id}')

        # Build context
        context = _build_context(scan)

        # Create or get notification channel
        channel_type = options.get('channel_type')
        email = options.get('email', 'test@example.com')

        if channel_type == 'email':
            config = {
                'recipients': [email],
                'subject_prefix': '[Test] Security Scanner'
            }
        elif channel_type == 'slack':
            config = {
                'webhook_url': 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
            }
        elif channel_type == 'teams':
            config = {
                'webhook_url': 'https://outlook.office.com/webhook/YOUR/TEAMS/WEBHOOK'
            }
        else:  # webhook
            config = {
                'webhook_url': 'https://httpbin.org/post',
                'secret': 'test-secret'
            }

        channel, created = NotificationChannel.objects.get_or_create(
            project=scan.target.project,
            name=f'Test {channel_type.title() if channel_type else "Email"} Channel',
            defaults={
                'type': channel_type,
                'config': config,
                'enabled': True
            }
        )

        if created:
            self.stdout.write(f'Created test {channel_type} channel: {channel.name}')

        # Create notification rule
        rule, created = NotificationRule.objects.get_or_create(
            project=scan.target.project,
            name=f'Test {channel_type.title() if channel_type else "Email"} Rule',
            defaults={
                'event': 'scan_completed',
                'channel': channel,
                'enabled': True,
                'severity_min': 'low'
            }
        )

        if created:
            self.stdout.write(f'Created test notification rule: {rule.name}')

        # Test synchronous dispatch
        self.stdout.write(f'Testing {channel_type} notification dispatch...')

        try:
            success, info = _dispatch_channel(channel, 'scan.completed', context)

            if success:
                self.stdout.write(
                    self.style.SUCCESS(f'[SUCCESS] Notification sent successfully via {channel_type}: {info}')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'[FAILED] Notification failed via {channel_type}: {info}')
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'[ERROR] Exception during notification dispatch: {e}')
            )

        # Clean up test data if we created it
        if not scan_id:
            scan.delete()
            self.stdout.write('Cleaned up test scan')

        self.stdout.write('Notification test completed.')