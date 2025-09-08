import json
from django.core.management.base import BaseCommand
from django.db import transaction
from compliance.models import (
    ComplianceFramework, ComplianceControl, ComplianceMapping
)


class Command(BaseCommand):
    help = 'Seed compliance frameworks, controls, and mappings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset all compliance data before seeding',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write('Resetting compliance data...')
            ComplianceMapping.objects.all().delete()
            ComplianceControl.objects.all().delete()
            ComplianceFramework.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Compliance data reset complete'))

        self.stdout.write('Seeding compliance frameworks...')

        # Seed OWASP Top Ten
        owasp_framework = self._create_owasp_framework()
        self._create_owasp_controls(owasp_framework)

        # Seed PCI DSS
        pci_framework = self._create_pci_framework()
        self._create_pci_controls(pci_framework)

        # Seed HIPAA
        hipaa_framework = self._create_hipaa_framework()
        self._create_hipaa_controls(hipaa_framework)

        # Seed GDPR
        gdpr_framework = self._create_gdpr_framework()
        self._create_gdpr_controls(gdpr_framework)

        # Seed ISO 27001
        iso_framework = self._create_iso_framework()
        self._create_iso_controls(iso_framework)

        # Seed NIST
        nist_framework = self._create_nist_framework()
        self._create_nist_controls(nist_framework)

        # Create mappings
        self._create_mappings()

        self.stdout.write(self.style.SUCCESS('Compliance data seeding complete'))

    def _create_owasp_framework(self):
        framework, created = ComplianceFramework.objects.get_or_create(
            name="OWASP Top Ten 2021",
            type=ComplianceFramework.FrameworkType.OWASP_TOP_TEN,
            defaults={
                'version': '2021',
                'description': 'OWASP Top Ten 2021 - Most Critical Web Application Security Risks',
                'is_active': True,
                'metadata': {
                    'source': 'https://owasp.org/www-project-top-ten/',
                    'year': 2021
                }
            }
        )
        if created:
            self.stdout.write(f'Created framework: {framework.name}')
        return framework

    def _create_owasp_controls(self, framework):
        controls_data = [
            {
                'control_id': 'A01:2021',
                'title': 'Broken Access Control',
                'description': 'Restrictions on what authenticated users are allowed to do are not properly enforced.',
                'severity': 'critical'
            },
            {
                'control_id': 'A02:2021',
                'title': 'Cryptographic Failures',
                'description': 'Failures related to cryptography (or lack thereof) which often lead to exposure of sensitive data.',
                'severity': 'high'
            },
            {
                'control_id': 'A03:2021',
                'title': 'Injection',
                'description': 'Injection occurs when untrusted data is sent to an interpreter as part of a command or query.',
                'severity': 'critical'
            },
            {
                'control_id': 'A04:2021',
                'title': 'Insecure Design',
                'description': 'A category for design-level vulnerabilities that are not covered by other categories.',
                'severity': 'high'
            },
            {
                'control_id': 'A05:2021',
                'title': 'Security Misconfiguration',
                'description': 'Security settings are not defined, implemented, or maintained properly.',
                'severity': 'high'
            },
            {
                'control_id': 'A06:2021',
                'title': 'Vulnerable and Outdated Components',
                'description': 'Using components with known vulnerabilities or outdated versions.',
                'severity': 'medium'
            },
            {
                'control_id': 'A07:2021',
                'title': 'Identification and Authentication Failures',
                'description': 'Authentication mechanisms are not implemented correctly.',
                'severity': 'high'
            },
            {
                'control_id': 'A08:2021',
                'title': 'Software and Data Integrity Failures',
                'description': 'Code and infrastructure that does not protect against integrity violations.',
                'severity': 'high'
            },
            {
                'control_id': 'A09:2021',
                'title': 'Security Logging and Monitoring Failures',
                'description': 'Insufficient logging and monitoring allows attackers to remain undetected.',
                'severity': 'medium'
            },
            {
                'control_id': 'A10:2021',
                'title': 'Server-Side Request Forgery',
                'description': 'SSRF flaws occur when a web application fetches a remote resource without validating the user-supplied URL.',
                'severity': 'high'
            }
        ]

        for control_data in controls_data:
            control, created = ComplianceControl.objects.get_or_create(
                framework=framework,
                control_id=control_data['control_id'],
                defaults={
                    'title': control_data['title'],
                    'description': control_data['description'],
                    'severity': control_data['severity'],
                    'type': 'requirement',
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(f'Created control: {control.control_id} - {control.title}')

    def _create_pci_framework(self):
        framework, created = ComplianceFramework.objects.get_or_create(
            name="PCI DSS 4.0",
            type=ComplianceFramework.FrameworkType.PCI_DSS,
            defaults={
                'version': '4.0',
                'description': 'Payment Card Industry Data Security Standard v4.0',
                'is_active': True,
                'metadata': {
                    'source': 'https://www.pcisecuritystandards.org/',
                    'year': 2022
                }
            }
        )
        if created:
            self.stdout.write(f'Created framework: {framework.name}')
        return framework

    def _create_pci_controls(self, framework):
        controls_data = [
            {
                'control_id': '1.1',
                'title': 'Processes and mechanisms for installing and maintaining network security controls',
                'description': 'Install and maintain network security controls.',
                'severity': 'high'
            },
            {
                'control_id': '2.1',
                'title': 'Configuration standards for system components',
                'description': 'Always change vendor-supplied defaults and remove or disable unnecessary default accounts.',
                'severity': 'high'
            },
            {
                'control_id': '3.1',
                'title': 'Protect stored account data',
                'description': 'Protect stored cardholder data.',
                'severity': 'critical'
            },
            {
                'control_id': '4.1',
                'title': 'Encrypt transmission of cardholder data',
                'description': 'Use strong cryptography and security protocols.',
                'severity': 'high'
            },
            {
                'control_id': '5.1',
                'title': 'Protect all systems against malware',
                'description': 'Deploy anti-malware solutions.',
                'severity': 'high'
            },
            {
                'control_id': '6.1',
                'title': 'Develop and maintain secure systems and applications',
                'description': 'Develop and maintain secure systems and software.',
                'severity': 'high'
            }
        ]

        for control_data in controls_data:
            control, created = ComplianceControl.objects.get_or_create(
                framework=framework,
                control_id=control_data['control_id'],
                defaults={
                    'title': control_data['title'],
                    'description': control_data['description'],
                    'severity': control_data['severity'],
                    'type': 'requirement',
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(f'Created control: {control.control_id} - {control.title}')

    def _create_hipaa_framework(self):
        framework, created = ComplianceFramework.objects.get_or_create(
            name="HIPAA Security Rule",
            type=ComplianceFramework.FrameworkType.HIPAA,
            defaults={
                'version': '2013',
                'description': 'Health Insurance Portability and Accountability Act Security Rule',
                'is_active': True,
                'metadata': {
                    'source': 'https://www.hhs.gov/hipaa/',
                    'year': 2013
                }
            }
        )
        if created:
            self.stdout.write(f'Created framework: {framework.name}')
        return framework

    def _create_hipaa_controls(self, framework):
        controls_data = [
            {
                'control_id': '164.308',
                'title': 'Administrative Safeguards',
                'description': 'Security management process, assigned security responsibility, etc.',
                'severity': 'high'
            },
            {
                'control_id': '164.310',
                'title': 'Physical Safeguards',
                'description': 'Facility access controls, workstation use, etc.',
                'severity': 'medium'
            },
            {
                'control_id': '164.312',
                'title': 'Technical Safeguards',
                'description': 'Access control, audit controls, integrity, etc.',
                'severity': 'high'
            }
        ]

        for control_data in controls_data:
            control, created = ComplianceControl.objects.get_or_create(
                framework=framework,
                control_id=control_data['control_id'],
                defaults={
                    'title': control_data['title'],
                    'description': control_data['description'],
                    'severity': control_data['severity'],
                    'type': 'requirement',
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(f'Created control: {control.control_id} - {control.title}')

    def _create_gdpr_framework(self):
        framework, created = ComplianceFramework.objects.get_or_create(
            name="GDPR",
            type=ComplianceFramework.FrameworkType.GDPR,
            defaults={
                'version': '2018',
                'description': 'General Data Protection Regulation',
                'is_active': True,
                'metadata': {
                    'source': 'https://gdpr-info.eu/',
                    'year': 2018
                }
            }
        )
        if created:
            self.stdout.write(f'Created framework: {framework.name}')
        return framework

    def _create_gdpr_controls(self, framework):
        controls_data = [
            {
                'control_id': 'Article 25',
                'title': 'Data Protection by Design and by Default',
                'description': 'Implement appropriate technical and organisational measures.',
                'severity': 'high'
            },
            {
                'control_id': 'Article 32',
                'title': 'Security of Processing',
                'description': 'Implement appropriate security measures.',
                'severity': 'high'
            },
            {
                'control_id': 'Article 33',
                'title': 'Notification of a Personal Data Breach',
                'description': 'Notify supervisory authority without undue delay.',
                'severity': 'critical'
            }
        ]

        for control_data in controls_data:
            control, created = ComplianceControl.objects.get_or_create(
                framework=framework,
                control_id=control_data['control_id'],
                defaults={
                    'title': control_data['title'],
                    'description': control_data['description'],
                    'severity': control_data['severity'],
                    'type': 'requirement',
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(f'Created control: {control.control_id} - {control.title}')

    def _create_iso_framework(self):
        framework, created = ComplianceFramework.objects.get_or_create(
            name="ISO 27001:2022",
            type=ComplianceFramework.FrameworkType.ISO_27001,
            defaults={
                'version': '2022',
                'description': 'Information Security Management Systems',
                'is_active': True,
                'metadata': {
                    'source': 'https://www.iso.org/standard/54534.html',
                    'year': 2022
                }
            }
        )
        if created:
            self.stdout.write(f'Created framework: {framework.name}')
        return framework

    def _create_iso_controls(self, framework):
        controls_data = [
            {
                'control_id': 'A.9.1',
                'title': 'Business requirements of access control',
                'description': 'Access control policy based on business requirements.',
                'severity': 'high'
            },
            {
                'control_id': 'A.12.1',
                'title': 'Operational procedures and responsibilities',
                'description': 'Document operating procedures and assign responsibilities.',
                'severity': 'medium'
            },
            {
                'control_id': 'A.18.1',
                'title': 'Compliance with legal and contractual requirements',
                'description': 'Identify applicable legislation and contractual requirements.',
                'severity': 'high'
            }
        ]

        for control_data in controls_data:
            control, created = ComplianceControl.objects.get_or_create(
                framework=framework,
                control_id=control_data['control_id'],
                defaults={
                    'title': control_data['title'],
                    'description': control_data['description'],
                    'severity': control_data['severity'],
                    'type': 'control',
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(f'Created control: {control.control_id} - {control.title}')

    def _create_nist_framework(self):
        framework, created = ComplianceFramework.objects.get_or_create(
            name="NIST Cybersecurity Framework",
            type=ComplianceFramework.FrameworkType.NIST,
            defaults={
                'version': '1.1',
                'description': 'NIST Cybersecurity Framework for Improving Critical Infrastructure Cybersecurity',
                'is_active': True,
                'metadata': {
                    'source': 'https://www.nist.gov/cyberframework',
                    'year': 2018
                }
            }
        )
        if created:
            self.stdout.write(f'Created framework: {framework.name}')
        return framework

    def _create_nist_controls(self, framework):
        controls_data = [
            {
                'control_id': 'ID.AM-1',
                'title': 'Physical devices and systems within the organization are inventoried',
                'description': 'Asset Management - Physical devices and systems are inventoried.',
                'severity': 'medium'
            },
            {
                'control_id': 'PR.AC-1',
                'title': 'Identities and credentials are issued, managed, verified and revoked',
                'description': 'Protective Technology - Access control mechanisms are implemented.',
                'severity': 'high'
            },
            {
                'control_id': 'DE.CM-1',
                'title': 'The network is monitored to detect potential cybersecurity events',
                'description': 'Detect - Network monitoring for cybersecurity events.',
                'severity': 'high'
            }
        ]

        for control_data in controls_data:
            control, created = ComplianceControl.objects.get_or_create(
                framework=framework,
                control_id=control_data['control_id'],
                defaults={
                    'title': control_data['title'],
                    'description': control_data['description'],
                    'severity': control_data['severity'],
                    'type': 'control',
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(f'Created control: {control.control_id} - {control.title}')

    def _create_mappings(self):
        self.stdout.write('Creating compliance mappings...')

        # Get controls for mapping
        owasp_injection = ComplianceControl.objects.filter(
            framework__type='owasp_top_ten',
            control_id='A03:2021'
        ).first()

        owasp_crypto = ComplianceControl.objects.filter(
            framework__type='owasp_top_ten',
            control_id='A02:2021'
        ).first()

        owasp_access = ComplianceControl.objects.filter(
            framework__type='owasp_top_ten',
            control_id='A01:2021'
        ).first()

        pci_encrypt = ComplianceControl.objects.filter(
            framework__type='pci_dss',
            control_id='4.1'
        ).first()

        # Create mappings
        mappings_data = [
            {
                'control': owasp_injection,
                'finding_type': 'sql_injection',
                'confidence': 95
            },
            {
                'control': owasp_injection,
                'finding_type': 'command_injection',
                'confidence': 90
            },
            {
                'control': owasp_crypto,
                'finding_type': 'weak_encryption',
                'confidence': 85
            },
            {
                'control': owasp_access,
                'finding_type': 'broken_access_control',
                'confidence': 80
            },
            {
                'control': pci_encrypt,
                'finding_type': 'weak_encryption',
                'confidence': 90
            }
        ]

        for mapping_data in mappings_data:
            if mapping_data['control']:
                mapping, created = ComplianceMapping.objects.get_or_create(
                    control=mapping_data['control'],
                    finding_type=mapping_data['finding_type'],
                    defaults={
                        'confidence': mapping_data['confidence'],
                        'mapping_type': 'automatic',
                        'is_active': True
                    }
                )
                if created:
                    self.stdout.write(f'Created mapping: {mapping.control.control_id} -> {mapping.finding_type}')