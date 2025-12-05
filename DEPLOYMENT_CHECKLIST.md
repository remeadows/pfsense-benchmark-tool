# Deployment Checklist

Use this checklist to deploy the pfSense Benchmark Tool to production.

## Pre-Deployment

### Code Preparation
- [ ] All code changes committed
- [ ] All tests passing locally
- [ ] Code reviewed (if team project)
- [ ] CHANGELOG.md updated
- [ ] Version number bumped in `app/__init__.py`

### Security Review
- [ ] No secrets in code
- [ ] `.gitignore` properly configured
- [ ] `.env.example` has all required variables
- [ ] SSH password storage removed/disabled
- [ ] Authentication enabled
- [ ] Host key verification enabled (production)
- [ ] Debug mode disabled

### Documentation
- [ ] README.md up to date
- [ ] CHANGELOG.md includes latest changes
- [ ] API documentation current (if applicable)
- [ ] Known issues documented

## Development Environment Setup

### Local Testing
- [ ] Create virtual environment: `python -m venv venv`
- [ ] Activate: `source venv/bin/activate` (or `venv\Scripts\activate` on Windows)
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Copy `.env.example` to `.env`
- [ ] Configure `.env` with test values
- [ ] Run tests: `python -m pytest tests/ -v`
- [ ] All tests pass
- [ ] Test coverage ≥ 70%

### SSH Key Setup
- [ ] Generate SSH key: `ssh-keygen -t ed25519 -f ~/.ssh/pfsense_key`
- [ ] Copy to all pfSense devices: `ssh-copy-id -i ~/.ssh/pfsense_key.pub admin@<ip>`
- [ ] Test connection: `ssh -i ~/.ssh/pfsense_key admin@<ip> "echo OK"`
- [ ] Add to SSH config or agent

### Application Testing
- [ ] Start app: `cd app && python app_new.py`
- [ ] Access at http://localhost:5000
- [ ] Login with test credentials
- [ ] Create test device
- [ ] Run auto-checks on test device
- [ ] Verify all checks complete
- [ ] Export CSV and verify
- [ ] Generate report and verify
- [ ] Test all routes work

## GitHub Setup (if using)

### Repository Creation
- [ ] Create GitHub repository
- [ ] Add repository description
- [ ] Choose Public or Private
- [ ] Initialize git: `git init`
- [ ] Add remote: `git remote add origin <url>`
- [ ] Create main branch: `git branch -M main`
- [ ] Initial commit: `git commit -m "Initial commit: v2.0.0"`
- [ ] Push: `git push -u origin main`

### Repository Configuration
- [ ] Enable Issues
- [ ] Enable Discussions (optional)
- [ ] Add topics/tags
- [ ] Configure branch protection for `main`
- [ ] Enable Dependabot
- [ ] Enable security scanning
- [ ] Add collaborators (if team)

### CI/CD Setup
- [ ] Verify `.github/workflows/ci.yml` present
- [ ] Verify `.github/workflows/release.yml` present
- [ ] Push triggers CI workflow
- [ ] CI workflow passes
- [ ] Codecov integration (optional)

### Documentation
- [ ] README.md displays correctly
- [ ] Add badges to README
- [ ] Issue templates working
- [ ] PR template working
- [ ] Wiki created (optional)

## Production Deployment

### Server Preparation

#### System Requirements
- [ ] Linux server (Ubuntu 22.04+ recommended)
- [ ] Python 3.10 or higher installed
- [ ] Git installed
- [ ] Sufficient disk space (1GB+)
- [ ] Network access to pfSense devices

#### User Setup
- [ ] Create dedicated user: `sudo useradd -m -s /bin/bash pfsense-tool`
- [ ] Switch to user: `sudo su - pfsense-tool`
- [ ] Create SSH directory: `mkdir -p ~/.ssh && chmod 700 ~/.ssh`

#### Firewall Configuration
- [ ] Open port 5000 (or custom port)
- [ ] Restrict access to trusted IPs
- [ ] Configure iptables/firewalld rules

### Application Installation

#### Clone Repository
```bash
- [ ] cd /opt
- [ ] sudo mkdir pfsense-benchmark-tool
- [ ] sudo chown pfsense-tool:pfsense-tool pfsense-benchmark-tool
- [ ] cd pfsense-benchmark-tool
- [ ] git clone <repository-url> .
```

#### Python Environment
```bash
- [ ] python3 -m venv venv
- [ ] source venv/bin/activate
- [ ] pip install --upgrade pip
- [ ] pip install -r requirements.txt
- [ ] pip install gunicorn
```

#### Configuration
```bash
- [ ] cp .env.example .env
- [ ] nano .env  # Edit configuration
- [ ] Set FLASK_DEBUG=False
- [ ] Set secure FLASK_SECRET_KEY
- [ ] Set secure ADMIN_PASSWORD
- [ ] Set SSH_KNOWN_HOSTS_CHECK=True
- [ ] Set appropriate SSH_TIMEOUT
```

#### SSH Keys (Production)
```bash
- [ ] Generate key: ssh-keygen -t ed25519 -f ~/.ssh/pfsense_prod_key
- [ ] Copy to all production pfSense devices
- [ ] Add to known_hosts: ssh-keyscan -H <ip> >> ~/.ssh/known_hosts
- [ ] Set correct permissions: chmod 600 ~/.ssh/pfsense_prod_key
- [ ] Test connections
```

#### Database Setup
```bash
- [ ] python3 -c "from app.models import Database; Database('reviews.db').init_db()"
- [ ] Verify database created: ls -lh reviews.db
- [ ] Set permissions: chmod 600 reviews.db
```

#### Data Files
```bash
- [ ] Copy pfsense_benchmark.json or .ckl file
- [ ] Verify file readable: cat pfsense_benchmark.json | head
- [ ] Set permissions: chmod 644 pfsense_benchmark.json
```

### WSGI Server Setup (Gunicorn)

#### Test Gunicorn
```bash
- [ ] cd /opt/pfsense-benchmark-tool
- [ ] source venv/bin/activate
- [ ] gunicorn -w 1 -b 127.0.0.1:5000 'app.app_new:app'
- [ ] Test in browser (if accessible)
- [ ] Stop with Ctrl+C
```

#### Create Systemd Service
```bash
- [ ] sudo nano /etc/systemd/system/pfsense-benchmark.service
```

Paste configuration:
```ini
[Unit]
Description=pfSense Benchmark Tool
After=network.target

[Service]
Type=notify
User=pfsense-tool
Group=pfsense-tool
WorkingDirectory=/opt/pfsense-benchmark-tool
Environment="PATH=/opt/pfsense-benchmark-tool/venv/bin"
ExecStart=/opt/pfsense-benchmark-tool/venv/bin/gunicorn \
    --workers 4 \
    --bind 127.0.0.1:5000 \
    --timeout 120 \
    --access-logfile /var/log/pfsense-benchmark-access.log \
    --error-logfile /var/log/pfsense-benchmark-error.log \
    'app.app_new:app'
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Enable Service
```bash
- [ ] sudo systemctl daemon-reload
- [ ] sudo systemctl enable pfsense-benchmark
- [ ] sudo systemctl start pfsense-benchmark
- [ ] sudo systemctl status pfsense-benchmark
- [ ] Verify running: ps aux | grep gunicorn
```

### Reverse Proxy Setup (Nginx)

#### Install Nginx
```bash
- [ ] sudo apt update
- [ ] sudo apt install nginx
- [ ] sudo systemctl enable nginx
```

#### Configure Nginx
```bash
- [ ] sudo nano /etc/nginx/sites-available/pfsense-benchmark
```

Paste configuration:
```nginx
server {
    listen 80;
    server_name pfsense-benchmark.example.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name pfsense-benchmark.example.com;

    # SSL Configuration
    ssl_certificate /etc/ssl/certs/pfsense-benchmark.crt;
    ssl_certificate_key /etc/ssl/private/pfsense-benchmark.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logging
    access_log /var/log/nginx/pfsense-benchmark-access.log;
    error_log /var/log/nginx/pfsense-benchmark-error.log;

    # Proxy to Gunicorn
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # Static files (if needed)
    location /static {
        alias /opt/pfsense-benchmark-tool/app/static;
        expires 30d;
    }
}
```

#### Enable Site
```bash
- [ ] sudo ln -s /etc/nginx/sites-available/pfsense-benchmark /etc/nginx/sites-enabled/
- [ ] sudo nginx -t
- [ ] sudo systemctl restart nginx
```

### SSL Certificate Setup

#### Option A: Let's Encrypt (Recommended)
```bash
- [ ] sudo apt install certbot python3-certbot-nginx
- [ ] sudo certbot --nginx -d pfsense-benchmark.example.com
- [ ] Test renewal: sudo certbot renew --dry-run
```

#### Option B: Self-Signed (Development Only)
```bash
- [ ] sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
      -keyout /etc/ssl/private/pfsense-benchmark.key \
      -out /etc/ssl/certs/pfsense-benchmark.crt
- [ ] sudo chmod 600 /etc/ssl/private/pfsense-benchmark.key
```

### Logging Setup

#### Configure Log Rotation
```bash
- [ ] sudo nano /etc/logrotate.d/pfsense-benchmark
```

Paste configuration:
```
/var/log/pfsense-benchmark-*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 pfsense-tool pfsense-tool
    sharedscripts
    postrotate
        systemctl reload pfsense-benchmark
    endscript
}
```

#### Verify Logging
```bash
- [ ] tail -f /var/log/pfsense-benchmark-access.log
- [ ] tail -f /var/log/pfsense-benchmark-error.log
```

## Post-Deployment

### Verification Tests

#### Basic Connectivity
- [ ] Access https://pfsense-benchmark.example.com
- [ ] SSL certificate valid
- [ ] No browser warnings
- [ ] Login page loads
- [ ] Authentication works

#### Functional Tests
- [ ] Login with admin credentials
- [ ] Create a device
- [ ] Edit device details
- [ ] Run auto-checks (test device)
- [ ] View compliance checklist
- [ ] Update item status
- [ ] Add review notes
- [ ] View dashboard
- [ ] Export CSV
- [ ] Generate report
- [ ] Delete test device

#### Security Tests
- [ ] Cannot access without authentication
- [ ] HTTP redirects to HTTPS
- [ ] Session timeout works
- [ ] SSH keys work (no passwords)
- [ ] Host key verification works
- [ ] Logs show security events

### Monitoring Setup

#### Health Check Script
```bash
- [ ] Create /opt/pfsense-benchmark-tool/healthcheck.sh
```

```bash
#!/bin/bash
curl -f -u admin:$ADMIN_PASSWORD http://127.0.0.1:5000/devices > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "OK"
    exit 0
else
    echo "FAIL"
    exit 1
fi
```

```bash
- [ ] chmod +x /opt/pfsense-benchmark-tool/healthcheck.sh
- [ ] Test: ./healthcheck.sh
```

#### Add to Monitoring
- [ ] Add to Nagios/Zabbix/etc.
- [ ] Monitor disk space
- [ ] Monitor process status
- [ ] Monitor log files for errors
- [ ] Set up alerting

### Backup Configuration

#### Automated Backups
```bash
- [ ] Create /opt/pfsense-benchmark-tool/backup.sh
```

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/backups/pfsense-benchmark
mkdir -p $BACKUP_DIR

# Backup database
cp /opt/pfsense-benchmark-tool/reviews.db \
   $BACKUP_DIR/reviews_$DATE.db

# Backup .env
cp /opt/pfsense-benchmark-tool/.env \
   $BACKUP_DIR/env_$DATE.backup

# Keep last 30 days
find $BACKUP_DIR -name "*.db" -mtime +30 -delete
```

```bash
- [ ] chmod +x /opt/pfsense-benchmark-tool/backup.sh
- [ ] Add to crontab: 0 2 * * * /opt/pfsense-benchmark-tool/backup.sh
```

### Documentation

#### Create Operations Document
- [ ] Server access procedures
- [ ] Restart procedures
- [ ] Backup/restore procedures
- [ ] Troubleshooting guide
- [ ] Emergency contacts
- [ ] Escalation procedures

#### User Training
- [ ] Create user accounts (if needed)
- [ ] Train users on interface
- [ ] Provide user documentation
- [ ] Set up support process

## Final Checklist

### Pre-Launch
- [ ] All tests pass
- [ ] Security review complete
- [ ] Performance tested
- [ ] Backup configured
- [ ] Monitoring active
- [ ] Documentation complete

### Launch Day
- [ ] Announce to users
- [ ] Monitor logs closely
- [ ] Be available for issues
- [ ] Document any problems
- [ ] Quick response to bugs

### Post-Launch
- [ ] Monitor for 24-48 hours
- [ ] Collect user feedback
- [ ] Address urgent issues
- [ ] Schedule regular reviews
- [ ] Plan next iteration

## Maintenance Schedule

### Daily
- [ ] Check service status
- [ ] Review error logs
- [ ] Monitor disk space
- [ ] Verify backups ran

### Weekly
- [ ] Review access logs
- [ ] Check for updates
- [ ] Test backup restoration
- [ ] Review performance

### Monthly
- [ ] Security patch review
- [ ] Dependency updates
- [ ] Certificate expiry check
- [ ] User access review
- [ ] Capacity planning

### Quarterly
- [ ] Full security audit
- [ ] Performance review
- [ ] User feedback review
- [ ] Feature planning
- [ ] Disaster recovery test

## Rollback Plan

If deployment fails:

1. **Stop services**:
   ```bash
   sudo systemctl stop pfsense-benchmark
   sudo systemctl stop nginx
   ```

2. **Restore previous version**:
   ```bash
   cd /opt/pfsense-benchmark-tool
   git checkout <previous-tag>
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Restore database** (if needed):
   ```bash
   cp /backups/pfsense-benchmark/reviews_<date>.db reviews.db
   ```

4. **Restart services**:
   ```bash
   sudo systemctl start pfsense-benchmark
   sudo systemctl start nginx
   ```

5. **Verify rollback**:
   - [ ] Application loads
   - [ ] Can login
   - [ ] Data intact
   - [ ] All features work

## Success Criteria

Deployment is successful when:

- [ ] Application accessible via HTTPS
- [ ] All functional tests pass
- [ ] No errors in logs (first hour)
- [ ] Users can login and work
- [ ] Auto-checks complete successfully
- [ ] Reports generate correctly
- [ ] Backups configured and working
- [ ] Monitoring active and alerting
- [ ] Documentation complete
- [ ] Team trained and confident

---

**Deployment Date**: _______________
**Deployed By**: _______________
**Version**: _______________
**Status**: ⬜ Success  ⬜ Rollback  ⬜ Partial

**Notes**:
_______________________________________________________
_______________________________________________________
_______________________________________________________
