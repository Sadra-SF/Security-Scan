# Security Scanner Demo Guide

## Overview
This guide provides comprehensive instructions for setting up, running, and demonstrating the Security Scanner project. This web-based application performs automated security scans on web applications and networks, identifies vulnerabilities, and generates detailed reports. It's built with Django (backend) and React (frontend).

## Prerequisites
Before starting, ensure you have the following installed on your system:
- **Python 3.8 or higher** (for backend)
- **Node.js 16 or higher** (for frontend)
- **PostgreSQL** (recommended for production) or **SQLite** (for development)
- **Redis** (for background task processing with Celery)
- **Git** (for cloning the repository)
- **Web browser** (Chrome, Firefox, or Edge recommended)

## Setup Instructions

### 1. Clone the Repository
```bash
git clone <repository-url>
cd security-scanner
```

### 2. Backend Setup (Django)
```bash
# Navigate to backend directory
cd backend/src

# Install Python dependencies
pip install -r requirements.txt

# Set up environment variables
cp ../../.env.example ../../.env
# Edit .env file with your database and other configurations

# Run database migrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser
# Follow prompts to create username, email, and password
```

### 3. Frontend Setup (React)
```bash
# Navigate to frontend directory
cd ../../frontend

# Install Node.js dependencies
npm install
```

### 4. Database Configuration
- For PostgreSQL: Update `.env` with your PostgreSQL connection details
- For SQLite (default): No additional configuration needed
- Run `python manage.py migrate` to create database tables

### 5. Additional Setup (Optional)
- Install OWASP ZAP for advanced dynamic scanning
- Configure Redis for Celery task queue
- Set up email/Slack notifications in settings

## Running the Application

### Development Mode
1. **Start Backend Server:**
   ```bash
   cd backend/src
   python manage.py runserver 8000
   ```
   The backend will run on http://localhost:8000

2. **Start Frontend Development Server:**
   ```bash
   cd frontend
   npm run dev
   ```
   The frontend will run on http://localhost:5173

3. **Access the Application:**
   Open your browser and navigate to http://localhost:5173

### Production Mode
```bash
# Build frontend
cd frontend
npm run build

# Start backend with production server
cd ../backend/src
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

## Demo Walkthrough

### Step 1: Login
1. Open http://localhost:5173 in your browser
2. Click "Login" in the top navigation
3. Use the admin credentials you created during setup
4. You'll be redirected to the dashboard

### Step 2: Create a Target
1. Navigate to "Targets" in the sidebar
2. Click "Add Target"
3. Fill in the details:
   - **Name:** My Test Application
   - **URL:** http://example.com (or use a test site)
   - **Type:** Web Application
   - **Description:** A sample web application for demonstration
4. Click "Save"

### Step 3: Run a Security Scan
1. Go to "Scans" in the sidebar
2. Click "New Scan"
3. Select your target from the dropdown
4. Choose scan type:
   - **Network Scan:** Basic port scanning
   - **Dynamic Scan:** Interactive security testing
5. Configure scan options (leave defaults for demo)
6. Click "Start Scan"
7. Monitor progress in the scans list

### Step 4: Review Findings
1. Once scan completes, click on the scan in the list
2. View the "Findings" tab
3. Examine identified vulnerabilities:
   - Severity levels (Critical, High, Medium, Low)
   - Vulnerability types (SQL Injection, XSS, etc.)
   - Detailed descriptions and recommendations
4. Click on individual findings to see evidence

### Step 5: Generate Reports
1. From the scan detail page, click "Generate Report"
2. Choose report format:
   - **HTML:** Web-viewable report
   - **PDF:** Printable document
   - **Markdown:** Text-based report
3. Select sections to include
4. Click "Generate"
5. Download and view the report

### Step 6: Explore Additional Features
1. **Compliance Checks:** View compliance status against standards
2. **Scheduled Scans:** Set up automated recurring scans
3. **Evidence Collection:** Review screenshots and logs
4. **Notifications:** Configure alerts for scan completion

## Key Features to Showcase

### 1. Multi-Type Scanning
- **Network Scanning:** Port scanning, service detection
- **Dynamic Scanning:** Interactive testing with OWASP ZAP integration
- **API Scanning:** RESTful API security testing
- **File Upload Scanning:** Test for upload vulnerabilities

### 2. Comprehensive Vulnerability Detection
- SQL Injection, XSS, CSRF detection
- Authentication and authorization issues
- Configuration weaknesses
- Information disclosure vulnerabilities

### 3. Evidence Collection
- Screenshots of vulnerable pages
- HTTP request/response logs
- Detailed vulnerability descriptions
- Proof-of-concept payloads

### 4. Report Generation
- Multiple formats (HTML, PDF, Markdown)
- Executive summaries
- Technical details
- Remediation recommendations
- Compliance mapping

### 5. Compliance Management
- OWASP Top 10 alignment
- PCI DSS compliance checks
- Custom compliance frameworks
- Automated compliance scoring

### 6. Automation Features
- Scheduled scans
- Continuous monitoring
- Integration with CI/CD pipelines
- Webhook notifications

### 7. User Management
- Role-based access control
- Team collaboration
- Audit logging
- Multi-tenant support

## Troubleshooting Guide

### Common Issues and Solutions

#### Backend Won't Start
**Problem:** `python manage.py runserver` fails
**Solutions:**
- Check Python version: `python --version` (should be 3.8+)
- Verify dependencies: `pip list | grep Django`
- Check database connection in `.env`
- Ensure no port conflicts on 8000

#### Frontend Build Fails
**Problem:** `npm run dev` or `npm install` errors
**Solutions:**
- Clear node_modules: `rm -rf node_modules && npm install`
- Check Node.js version: `node --version`
- Update npm: `npm install -g npm@latest`
- Check for missing dependencies in package.json

#### Database Connection Issues
**Problem:** Migration or connection errors
**Solutions:**
- For PostgreSQL: Verify connection string in `.env`
- For SQLite: Ensure file permissions on db.sqlite3
- Check database server is running
- Run `python manage.py dbshell` to test connection

#### Scan Fails to Start
**Problem:** Scans remain in "pending" status
**Solutions:**
- Check Redis is running: `redis-cli ping`
- Start Celery worker: `celery -A config worker -l info`
- Verify target URL is accessible
- Check scanner configurations

#### Port Conflicts
**Problem:** "Address already in use" errors
**Solutions:**
- Change backend port: `python manage.py runserver 8001`
- Change frontend port: Edit `vite.config.ts` or use `npm run dev -- --port 5174`
- Kill conflicting processes: `lsof -ti:8000 | xargs kill -9`

#### OWASP ZAP Integration Issues
**Problem:** Dynamic scans fail
**Solutions:**
- Install OWASP ZAP: Download from official site
- Start ZAP API: `zap.sh -daemon -port 8080`
- Update ZAP path in scanner configuration
- Check firewall settings for ZAP port

#### Memory/Performance Issues
**Problem:** Application runs slowly or crashes
**Solutions:**
- Increase system memory
- Use lighter database (SQLite for dev)
- Disable unnecessary scanners
- Monitor resource usage with `top` or Task Manager

### Getting Help
- Check application logs in `backend/src/logs/`
- Review browser console for frontend errors
- Test API endpoints directly at http://localhost:8000/api/
- Consult Django/React documentation for framework-specific issues

## Presentation Tips

### Preparation
- **Test Everything:** Run through the entire demo beforehand
- **Prepare Sample Data:** Create test targets and run sample scans
- **Backup Plan:** Have screenshots/videos if live demo fails
- **Time Management:** Allocate 15-20 minutes for the demo

### During Presentation
- **Start with Overview:** Explain what the tool does in 2-3 minutes
- **Show Real Value:** Demonstrate actual vulnerability detection
- **Explain Concepts:** Briefly cover security basics without jargon overload
- **Highlight Automation:** Emphasize time-saving features
- **Be Interactive:** Ask audience about their security concerns

### Demo Script Outline
1. **Introduction (2 min):**
   - "This is a comprehensive security scanner for web applications"
   - "It automates vulnerability detection and report generation"

2. **Setup Demo (3 min):**
   - Show quick setup process
   - Mention ease of deployment

3. **Core Functionality (5 min):**
   - Create target → Run scan → View findings → Generate report
   - Walk through each step clearly

4. **Advanced Features (3 min):**
   - Show compliance checks
   - Demonstrate scheduling
   - Mention integrations

5. **Q&A (2 min):**
   - Address common questions
   - Discuss customization options

### Key Points to Emphasize
- **Ease of Use:** User-friendly interface, no security expertise required
- **Comprehensive Coverage:** Multiple scan types and vulnerability categories
- **Automation:** Scheduled scans reduce manual effort
- **Reporting:** Professional reports for stakeholders
- **Scalability:** Handles multiple targets and large applications
- **Integration:** Works with existing development workflows

### Handling Questions
- **Technical Depth:** Have architecture diagrams ready
- **Performance:** Share benchmark results
- **Cost:** Discuss deployment options and resource requirements
- **Security:** Explain how the tool itself is secure
- **Comparisons:** Know how it differs from commercial tools

### Backup Materials
- **Screenshots:** Key interface screens
- **Sample Reports:** Example vulnerability reports
- **Architecture Diagram:** High-level system overview
- **Feature List:** Comprehensive capability summary

Remember to speak clearly, maintain eye contact, and demonstrate enthusiasm for the project. The goal is to show both the technical capabilities and practical value of the security scanner.