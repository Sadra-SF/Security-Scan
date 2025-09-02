# Security Scanner User Manual

## Table of Contents
1. [Introduction](#introduction)
2. [Installation and Setup](#installation-and-setup)
3. [Getting Started](#getting-started)
4. [User Interface Guide](#user-interface-guide)
5. [Scanning Capabilities](#scanning-capabilities)
6. [Reporting Features](#reporting-features)
7. [Compliance Features](#compliance-features)
8. [API Documentation](#api-documentation)
9. [Configuration](#configuration)
10. [Troubleshooting](#troubleshooting)
11. [Appendices](#appendices)

## Introduction

The Security Scanner is a comprehensive web application security testing platform designed to help organizations identify and remediate security vulnerabilities in their applications and infrastructure. Built with Django (backend) and React (frontend), it provides automated scanning capabilities, compliance assessment, and detailed reporting.

### Key Features
- **Multi-Type Scanning**: Static, dynamic, and network vulnerability scanning
- **Compliance Assessment**: Support for OWASP Top Ten, PCI DSS, HIPAA, GDPR, and ISO 27001
- **Flexible Reporting**: PDF, HTML, Markdown, and CSV report formats
- **Notification System**: Email, Slack, Teams, and webhook integrations
- **Scheduling**: Automated recurring scans
- **API-First Design**: RESTful API for integration with other tools
- **Multi-Tenant**: Project-based organization with role-based access

### Architecture Overview
- **Backend**: Django REST Framework with Celery for async tasks
- **Frontend**: React with TypeScript
- **Database**: PostgreSQL (production) or SQLite (development)
- **Task Queue**: Redis + Celery
- **Scanners**: OWASP ZAP (dynamic), Nmap (network), custom static analyzers

## Installation and Setup

### Prerequisites
- Python 3.8+
- Node.js 16+
- PostgreSQL (recommended) or SQLite
- Redis (for Celery)
- Docker (optional, for containerized deployment)

### Backend Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd security-scanner
   ```

2. **Install Python dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Database setup**:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

5. **Start services**:
   ```bash
   # Start Redis (if not using Docker)
   redis-server

   # Start Celery worker
   celery -A api_server worker -l info

   # Start Django server
   python manage.py runserver
   ```

### Frontend Setup

1. **Install dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Start development server**:
   ```bash
   npm start
   ```

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build
```

## Getting Started

### First Login
1. Access the application at `http://localhost:3000`
2. Log in with the superuser credentials created during setup
3. Create your first project

### Creating Your First Scan

1. **Add a Target**:
   - Navigate to Targets page
   - Click "Add Target"
   - Enter target URL or IP address
   - Select target type (web, API, network)

2. **Configure Scan Profile**:
   - Choose scanner types (static, dynamic, network)
   - Set scan parameters
   - Configure authentication if needed

3. **Run Scan**:
   - Start manual scan
   - Monitor progress in real-time
   - Review findings as they are discovered

### Understanding Findings
- **Severity Levels**: Critical, High, Medium, Low, Info
- **Categories**: Injection, XSS, CSRF, misconfiguration, etc.
- **Status**: Open, Resolved, False Positive
- **Evidence**: Detailed information about each finding

## User Interface Guide

### Dashboard
The dashboard provides an overview of:
- Recent scan activity
- Vulnerability distribution by severity
- Compliance status summary
- Active projects and targets

### Scans Management
- **List View**: Browse all scans with filtering and search
- **Detail View**: Monitor scan progress and view results
- **Create Scan**: Configure new scans with custom parameters

### Findings Management
- **Bulk Operations**: Update multiple findings status
- **Filtering**: Filter by severity, status, category, target
- **Evidence View**: Detailed information and remediation steps

### Reports
- **Generate Reports**: Create reports in multiple formats
- **Download**: Export reports for offline review
- **Scheduled Reports**: Automate report generation

### Compliance Dashboard
- **Framework Selection**: Choose compliance frameworks
- **Assessment Results**: View compliance scores and gaps
- **Control Mapping**: Map findings to specific controls

## Scanning Capabilities

### Static Scanning
Analyzes source code and configuration files for vulnerabilities:
- **SQL Injection**: Detects unsafe SQL query patterns
- **XSS**: Identifies cross-site scripting vulnerabilities
- **CSRF**: Checks for cross-site request forgery issues
- **Configuration Analysis**: Reviews security settings

**Example Configuration**:
```json
{
  "static": {
    "sqli": {
      "enabled": true,
      "patterns": ["SELECT.*FROM.*WHERE.*=.*['\"]\s*\+", "exec\s*\("]
    }
  }
}
```

### Dynamic Scanning
Uses OWASP ZAP to perform active scanning:
- **Active Scan**: Automated vulnerability detection
- **Baseline Scan**: Passive scanning for common issues
- **API Scanning**: REST and GraphQL API testing

**Example Configuration**:
```json
{
  "dynamic": {
    "zap": {
      "url": "https://example.com",
      "mode": "active",
      "zap_host": "127.0.0.1",
      "zap_port": 8080
    }
  }
}
```

### Network Scanning
Uses Nmap for network reconnaissance:
- **Port Scanning**: Identify open ports and services
- **OS Detection**: Determine operating system versions
- **Service Versioning**: Detect service versions and vulnerabilities

**Example Configuration**:
```json
{
  "network": {
    "nmap": {
      "targets": ["192.168.1.0/24"],
      "scan_args": "-sV -O"
    }
  }
}
```

## Reporting Features

### Report Types
- **PDF Reports**: Professional formatted reports with charts
- **HTML Reports**: Web-viewable reports with interactive elements
- **Markdown Reports**: Text-based reports for documentation
- **CSV Exports**: Data exports for analysis in other tools

### Report Templates
- **Scan Reports**: Detailed findings from specific scans
- **Compliance Reports**: Framework-specific compliance assessments
- **Executive Summaries**: High-level overviews for management

### Custom Reporting
```python
# Generate custom report
from reports.utils import findings_queryset_with_compliance

filters = {
    'project_id': 1,
    'severity': ['high', 'critical'],
    'created_since_days': 30
}

findings = findings_queryset_with_compliance(filters)
# Process findings for custom report
```

## Compliance Features

### Supported Frameworks
- **OWASP Top Ten**: Web application security standards
- **PCI DSS**: Payment card industry data security standard
- **HIPAA**: Health insurance portability and accountability act
- **GDPR**: General data protection regulation
- **ISO 27001**: Information security management systems

### Compliance Assessment
```python
from compliance.assessment import ComplianceAssessmentService

# Assess target compliance
assessment = ComplianceAssessmentService.assess_target_compliance(
    target=target,
    framework=framework,
    project=project
)

print(f"Compliance Status: {assessment.compliance_status}")
print(f"Overall Score: {assessment.overall_score}%")
```

### Control Mapping
- **Automatic Mapping**: AI-powered mapping of findings to controls
- **Manual Mapping**: Custom mapping for specific requirements
- **Confidence Scoring**: Reliability ratings for mappings

## API Documentation

### Authentication
The API uses JWT (JSON Web Tokens) for authentication:

```bash
# Obtain token
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}'

# Use token
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/scans/
```

### Core Endpoints

#### Scans
```bash
# List scans
GET /api/scans/

# Create scan
POST /api/scans/
{
  "target": "https://example.com",
  "scanner": "zap",
  "config": {"mode": "active"}
}

# Get scan details
GET /api/scans/{id}/
```

#### Findings
```bash
# List findings
GET /api/findings/?severity=high&status=open

# Update finding
PATCH /api/findings/{id}/
{
  "status": "resolved",
  "notes": "Fixed with input validation"
}
```

#### Reports
```bash
# Generate report
POST /api/reports/
{
  "project": 1,
  "format": "pdf",
  "filters": {"severity": ["high", "critical"]}
}

# Download report
GET /api/reports/{id}/download/
```

### Webhooks
Configure webhooks for real-time notifications:

```json
{
  "name": "Slack Integration",
  "url": "https://hooks.slack.com/services/...",
  "secret": "webhook-secret",
  "headers": {"Content-Type": "application/json"}
}
```

## Configuration

### Environment Variables
```bash
# Database
POSTGRES_HOST=localhost
POSTGRES_DB=security_scanner
POSTGRES_USER=scanner
POSTGRES_PASSWORD=scannerpass

# Redis/Celery
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0

# Security
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=False

# Scanners
ZAP_HOST=zap
ZAP_PORT=8090
ZAP_API_KEY=changeme
```

### Scanner Configuration
```python
# settings.py
SCANNER_DEFAULTS = {
    "USER_AGENT": "SecurityScanner/0.1",
    "HTTP_TIMEOUT_SECS": 5,
    "STATIC": {"SOFT_TIME_LIMIT": 480, "HARD_TIME_LIMIT": 600},
    "DYNAMIC": {"SOFT_TIME_LIMIT": 1500, "HARD_TIME_LIMIT": 1800},
    "NETWORK": {"SOFT_TIME_LIMIT": 300, "HARD_TIME_LIMIT": 600}
}
```

### Notification Settings
```python
NOTIFICATIONS_DEFAULTS = {
    "threshold_severity": "high",
    "email_from": "scanner@company.com"
}
```

## Troubleshooting

### Common Issues

#### Scanner Not Starting
**Problem**: Dynamic scanner fails to initialize
**Solution**:
1. Ensure OWASP ZAP is installed and accessible
2. Check ZAP_HOST and ZAP_PORT in configuration
3. Verify API key if authentication is enabled

#### Database Connection Errors
**Problem**: Unable to connect to PostgreSQL
**Solution**:
```bash
# Check PostgreSQL service
sudo systemctl status postgresql

# Verify connection
psql -h localhost -U scanner -d security_scanner
```

#### Celery Tasks Not Processing
**Problem**: Background tasks remain pending
**Solution**:
```bash
# Check Celery worker status
celery -A api_server inspect active

# Restart worker
celery -A api_server worker --loglevel=info
```

#### High Memory Usage
**Problem**: Application consumes excessive memory
**Solution**:
- Reduce concurrent scan limits
- Implement scan queuing
- Monitor and restart services periodically

### Logs and Debugging

#### Enable Debug Mode
```bash
export DJANGO_DEBUG=True
export DJANGO_LOG_LEVEL=DEBUG
```

#### View Application Logs
```bash
# Django logs
tail -f backend/src/logs/django.log

# Celery logs
tail -f backend/src/logs/celery.log

# Scanner logs
tail -f backend/src/logs/scanners.log
```

#### Database Query Optimization
```python
# Add database indexes for performance
from django.db import models

class Scan(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=['target', 'status']),
            models.Index(fields=['created_at']),
        ]
```

## Appendices

### A. Supported File Types
- **Static Analysis**: .py, .js, .ts, .java, .php, .html, .xml, .json, .yaml
- **Configuration Files**: nginx.conf, apache.conf, web.config, .env
- **Documentation**: README.md, CHANGELOG.md, SECURITY.md

### B. Severity Classification
- **Critical**: Immediate threat to production systems
- **High**: Significant security risk requiring urgent attention
- **Medium**: Moderate risk that should be addressed
- **Low**: Minor issues with limited impact
- **Info**: Informational findings for awareness

### C. Compliance Control Examples

#### OWASP Top Ten Mapping
- **A01:2021 - Broken Access Control**: Authentication bypass vulnerabilities
- **A02:2021 - Cryptographic Failures**: Weak encryption, exposed secrets
- **A03:2021 - Injection**: SQL injection, command injection
- **A04:2021 - Insecure Design**: Architectural security flaws

#### PCI DSS Requirements
- **Requirement 6**: Develop and maintain secure systems and applications
- **Requirement 11**: Regularly test security systems and processes
- **Requirement 12**: Maintain a policy that addresses information security

### D. API Rate Limits
- **Authenticated Requests**: 1000/hour per user
- **Scan Operations**: 10 concurrent scans per project
- **Report Generation**: 50 reports/hour per project

### E. Backup and Recovery
```bash
# Database backup
pg_dump security_scanner > backup.sql

# Restore database
psql security_scanner < backup.sql

# File system backup
tar -czf reports_backup.tar.gz var/reports/
```

### F. Security Considerations
- Store sensitive configuration in environment variables
- Use HTTPS in production
- Implement proper authentication and authorization
- Regularly update dependencies
- Monitor for security vulnerabilities in third-party packages

---

**Version**: 0.1.0
**Last Updated**: September 2025
**Contact**: support@security-scanner.local