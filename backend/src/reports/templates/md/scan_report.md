{% extends "reports/md/base.md" %}
{% block title %}{{ report.title|default:"Security Scanner Report" }}{% endblock %}
{% block content %}
## Executive Summary

This security assessment report provides an overview of vulnerabilities and security findings discovered during the scanning process for project **{{ project.name }}**.

### Statistics
- **Total Findings:** {{ findings|length }}
- **Critical Issues:** {{ grouped.critical|default([])|length }}
- **High Severity:** {{ grouped.high|default([])|length }}
- **Medium Severity:** {{ grouped.medium|default([])|length }}
- **Low Severity:** {{ grouped.low|default([])|length }}
- **Informational:** {{ grouped.info|default([])|length }}

## Vulnerability Breakdown

| Severity | Count | Description |
|----------|-------|-------------|
| 🔴 Critical | {{ grouped.critical|default([])|length }} | Immediate security risks requiring urgent attention |
| 🟠 High | {{ grouped.high|default([])|length }} | Significant security vulnerabilities |
| 🟡 Medium | {{ grouped.medium|default([])|length }} | Moderate security concerns |
| 🟢 Low | {{ grouped.low|default([])|length }} | Minor security issues |
| 🔵 Info | {{ grouped.info|default([])|length }} | Informational findings |

## Detailed Findings

{% for severity, cats in grouped.items %}
### {{ severity|upper }} Severity Findings

{% for category, items in cats.items %}
#### Category: {{ category }}

{% for f in items %}
**{{ f.title }}**

- **Status:** {{ f.status }}
- **Target:** {{ f.target.name }}
{% if f.scan_id %}- **Scan:** {{ f.scan_id }}{% endif %}
- **First seen:** {{ f.first_seen_at|date:"M j, Y g:i A" }}
- **Last seen:** {{ f.last_seen_at|date:"M j, Y g:i A" }}
{% if f.metadata.category %}- **Category:** {{ f.metadata.category }}{% endif %}
{% if f.locations and f.locations.0 %}
  {% with loc=f.locations.0 %}
- **Location:** {% if loc.url %}{{ loc.url }}{% elif loc.file %}{{ loc.file }}{% else %}{{ loc }}{% endif %}{% if loc.param %} (param={{ loc.param }}){% endif %}
  {% endwith %}
{% endif %}
- **Description:** {{ f.description|default:"-" }}
- **Plugin:** {{ f.metadata.plugin_key|default:f.metadata.plugin|default:"-" }}

{% comment %}Compliance tags{% endcomment %}
{% if f.compliance_tags.all %}
**Compliance Tags:** {% for t in f.compliance_tags.all %}{{ t.framework|default:"" }}{% if t.framework %}:{% endif %}{{ t.slug|default:t.name }}{% if not forloop.last %}, {% endif %}{% endfor %}
{% elif f.compliancetag_set.all %}
**Compliance Tags:** {% for t in f.compliancetag_set.all %}{{ t.framework|default:"" }}{% if t.framework %}:{% endif %}{{ t.slug|default:t.name }}{% if not forloop.last %}, {% endif %}{% endfor %}
{% endif %}

---
{% endfor %}
{% endfor %}
{% empty %}
*No findings match the applied filters.*
{% endfor %}

## Remediation Recommendations

### Priority Actions
- **Critical Issues:** Address all critical severity findings immediately as they pose the highest security risk
- **High Severity:** Resolve high severity issues within the next sprint or development cycle
- **Input Validation:** Implement proper input validation and sanitization for all user inputs
- **Authentication:** Ensure all sensitive operations require proper authentication and authorization
- **Updates:** Keep all software dependencies and frameworks up to date with the latest security patches

## Compliance Mapping

This report includes compliance mappings for the following frameworks:
- **OWASP Top 10:** Web application security standards
- **PCI DSS:** Payment card industry data security standards
- **HIPAA:** Health insurance portability and accountability act
- **GDPR:** General data protection regulation
- **ISO 27001:** Information security management systems

Findings are tagged with relevant compliance frameworks where applicable.
{% endblock %}