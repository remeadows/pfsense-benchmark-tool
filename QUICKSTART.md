# Quick Start Guide

Get the pfSense Benchmark Tool running in 5 minutes!

## Prerequisites

- Python 3.10 or higher
- SSH access to pfSense device(s)
- Windows, macOS, or Linux

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example config
cp .env.example .env

# Edit .env file
notepad .env  # Windows
nano .env     # Linux/Mac
```

Minimum required changes in `.env`:
```bash
FLASK_SECRET_KEY=your-random-secret-key-here
ADMIN_USERNAME=admin
ADMIN_PASSWORD=YourSecurePassword123
```

### 3. Set Up SSH Keys

```bash
# Generate key
ssh-keygen -t ed25519 -f ~/.ssh/pfsense_key

# Copy to pfSense device
ssh-copy-id -i ~/.ssh/pfsense_key.pub admin@192.168.1.1
```

### 4. Start Application

```bash
cd app
python app_new.py
```

Visit: `http://localhost:5000`

## First Time Usage

### Add Your First Device

1. Click **"New Device"**
2. Fill in:
   - **Name**: "Main Firewall"
   - **Hostname**: "fw.example.com"
   - **Management IP**: "192.168.1.1"
   - **SSH User**: "admin"
3. Click **"Save"**

### Run Automated Checks

1. Click on your device
2. Click **"Run Auto-Checks"**
3. Wait ~30 seconds
4. Review results

### Manual Review

1. Click on any control to add notes
2. Update status if needed
3. Click **"Save Review"**

### Generate Report

1. Click **"Dashboard"** for summary
2. Click **"Export CSV"** for detailed report
3. Click **"Generate Report"** for formatted view

## Common Issues

### "Authentication failed" (SSH)

**Solution**: Verify SSH key setup
```bash
# Test manually
ssh -i ~/.ssh/pfsense_key admin@192.168.1.1

# If fails, re-copy key
ssh-copy-id -i ~/.ssh/pfsense_key.pub admin@192.168.1.1
```

### "Module not found" error

**Solution**: Install requirements
```bash
pip install -r requirements.txt
```

### Browser shows "Authentication Required"

This is correct! Enter:
- Username: `admin` (or whatever you set in `.env`)
- Password: Your password from `.env`

### "Cannot read config.xml"

**Solutions**:
1. Verify SSH user has admin privileges
2. Check management IP is correct
3. Ensure pfSense SSH service is running

## Next Steps

- Read [README.md](README.md) for full documentation
- Check [MIGRATION.md](MIGRATION.md) if upgrading from v1.0
- Review [REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md) for technical details

## Getting Help

1. Check error logs in terminal
2. Review [README.md](README.md) troubleshooting section
3. Ensure SSH keys are set up correctly

## Security Checklist

Before deploying to production:

- [ ] Change default password in `.env`
- [ ] Generate secure `FLASK_SECRET_KEY`
- [ ] Set `FLASK_DEBUG=False`
- [ ] Enable SSH host key checking: `SSH_KNOWN_HOSTS_CHECK=True`
- [ ] Use HTTPS (reverse proxy)
- [ ] Restrict network access
- [ ] Regular database backups

## Production Deployment

For production, use a proper WSGI server:

```bash
# Install gunicorn
pip install gunicorn

# Run with 4 workers
gunicorn -w 4 -b 127.0.0.1:5000 'app.app_new:app'
```

Consider:
- Reverse proxy (nginx/Apache)
- Systemd service
- Firewall rules
- SSL certificate

See [README.md](README.md) for detailed production setup.

---

That's it! You should now have a working pfSense Benchmark Tool.
