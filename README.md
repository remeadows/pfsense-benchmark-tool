# pfSense Benchmark Tool

[![CI](https://github.com/remeadows/pfsense-benchmark-tool/workflows/CI/badge.svg)](https://github.com/remeadows/pfsense-benchmark-tool/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A Flask web application for conducting pfSense CIS/STIG security benchmark assessments. Track compliance across multiple pfSense devices, run automated checks via SSH, and generate compliance reports.

## Features

- **Multi-Device Management**: Track compliance for multiple pfSense firewalls
- **Automated Checks**: SSH-based automated compliance verification (28+ checks)
- **Manual Review**: Review and document compliance status for each control
- **Compliance Reports**: Generate detailed reports and export to CSV
- **CKL/JSON Support**: Import DISA STIG Checklist (CKL) or JSON formats
- **Secure by Design**: Uses defusedxml, key-based SSH auth, password hashing

## Security Improvements (v2.0)

This refactored version addresses all security concerns:

- ✅ **XML Security**: Uses `defusedxml` to prevent XXE and XML bomb attacks
- ✅ **SSH Security**: Key-based authentication only, optional known_hosts verification
- ✅ **SQL Injection**: All queries use parameterized statements
- ✅ **Authentication**: HTTP Basic Auth with password hashing (Werkzeug)
- ✅ **No Password Storage**: SSH passwords never stored in database
- ✅ **Secure File Operations**: Uses SFTP instead of command injection
- ✅ **Proper Error Handling**: Specific exception handling with logging
- ✅ **Configuration Security**: Environment variables for sensitive config

## Installation

### Requirements

- Python 3.10+
- SSH access to pfSense devices (key-based authentication)
- pfSense 2.6+ (tested on 2.7)

### Setup

1. **Clone the repository**:
   ```bash
   git clone <repo-url>
   cd Pfsense_Benchmark_Tool
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

   Important settings in `.env`:
   - `FLASK_SECRET_KEY`: Generate a random secret key
   - `ADMIN_USERNAME` / `ADMIN_PASSWORD`: Set authentication credentials
   - `SSH_KNOWN_HOSTS_CHECK`: Set to `True` for production (validates SSH host keys)
   - `FLASK_DEBUG`: Set to `False` for production

4. **Set up SSH keys**:
   ```bash
   # Generate SSH key if you don't have one
   ssh-keygen -t ed25519 -f ~/.ssh/pfsense_key

   # Copy to pfSense device
   ssh-copy-id -i ~/.ssh/pfsense_key.pub admin@pfsense-ip
   ```

5. **Prepare benchmark data**:

   **Option A**: Use existing CKL file:
   - Place your `pfsense_benchmark.ckl` in the root directory

   **Option B**: Convert Excel to JSON:
   ```bash
   python scripts/parse_benchmark.py "path/to/Pf Sense Benchmark.xlsx"
   ```

6. **Initialize database**:
   ```bash
   python -c "from app.models import Database; Database('reviews.db').init_db()"
   ```

## Usage

### Running the Application

**Development**:
```bash
cd app
python app_new.py
```

**Production** (use a proper WSGI server):
```bash
pip install gunicorn
gunicorn -w 4 -b 127.0.0.1:5000 'app.app_new:app'
```

Access the application at `http://localhost:5000`

Default credentials: `admin` / `change-this-password` (change in `.env`!)

### Workflow

1. **Add a Device**:
   - Navigate to "Devices" → "New Device"
   - Enter device name, hostname, management IP, and SSH username
   - Save

2. **Run Automated Checks**:
   - Go to device checklist
   - Click "Run Auto-Checks"
   - Wait for SSH-based checks to complete (28+ controls)

3. **Manual Review**:
   - Review each control item
   - Update status (Compliant, Non Compliant, Non Applicable, Not Reviewed)
   - Add notes for each item

4. **Generate Reports**:
   - View dashboard for compliance summary
   - Export to CSV for documentation
   - Generate formatted report

### Automated Checks

The tool automatically verifies 28+ CIS/STIG controls via SSH:

**System Configuration** (1.x):
- SSH banner configuration
- MOTD settings
- Hostname configuration
- DNS server settings
- IPv6 status
- HTTPS web management
- NTP configuration

**Access Control** (2.x):
- Session timeout settings
- LDAP/RADIUS authentication

**Services** (3.x):
- SNMP configuration
- Captive portal status

**Firewall Rules** (4.x):
- WAN rule analysis (ANY source/dest/service)
- Disabled rules
- Logging requirements
- ICMP rule specificity

**Advanced Configuration** (5.x):
- SNMP traps
- Timezone settings
- DNSSEC
- VPN configuration
- OpenVPN TLS/cipher settings

**Logging** (6.x):
- Syslog configuration

## Project Structure

```
Pfsense_Benchmark_Tool/
├── app/
│   ├── __init__.py
│   ├── app_new.py          # Main Flask application (REFACTORED)
│   ├── config.py           # Configuration management
│   ├── models.py           # Database models and enums
│   ├── parsers.py          # Secure XML/JSON parsing
│   ├── ssh_client.py       # Secure SSH client wrapper
│   ├── auth.py             # Authentication module
│   ├── auto_checks.py      # Data-driven automated checks
│   ├── reports.py          # Report generation logic
│   └── templates/          # HTML templates
│       ├── layout.html
│       ├── devices.html
│       ├── checklist.html
│       ├── item.html
│       ├── dashboard.html
│       ├── report.html
│       └── error.html      # Error pages
├── scripts/
│   └── parse_benchmark.py  # Excel to JSON converter
├── tests/
│   ├── test_models.py      # Unit tests for models
│   └── test_reports.py     # Unit tests for reports
├── .env.example            # Example environment variables
├── requirements.txt        # Python dependencies
├── README.md              # This file
└── pfsense_benchmark.json # Checklist data (or .ckl)
```

## Architecture

### Modular Design

The refactored application separates concerns:

- **config.py**: Environment-based configuration
- **models.py**: Database operations and data models
- **parsers.py**: Secure file parsing (XML/JSON)
- **ssh_client.py**: Secure SSH operations with context managers
- **auth.py**: Authentication and authorization
- **auto_checks.py**: Data-driven check registry
- **reports.py**: Business logic for summaries and reports

### Security Best Practices

- **No Hardcoded Secrets**: All sensitive data in environment variables
- **Principle of Least Privilege**: SSH uses key-based auth only
- **Defense in Depth**: Multiple layers of validation and sanitization
- **Secure by Default**: SSH host key checking enabled by default
- **Logging**: Comprehensive logging for audit trails

### Database Schema

**devices** table:
- `id`: Primary key
- `name`: Device name (required)
- `hostname`: Device hostname
- `notes`: Free-text notes
- `mgmt_ip`: Management IP for SSH
- `ssh_user`: SSH username

**reviews** table:
- `device_id`: Foreign key to devices
- `item_index`: Checklist item index
- `status`: Compliance status
- `note`: Review notes
- Primary key: `(device_id, item_index)`

## Testing

Run unit tests:

```bash
python -m unittest discover tests
```

Run specific test:
```bash
python tests/test_models.py
```

## Migration from Old Version

If you have an existing `reviews.db` from the old app.py:

1. **Backup your database**:
   ```bash
   cp reviews.db reviews.db.backup
   ```

2. **The schema is compatible** - no migration needed for the database

3. **Update imports**:
   - Replace `app.py` usage with `app_new.py`
   - Update any scripts that import from `app.py`

4. **Set up `.env` file** with your configuration

5. **Test the migration**:
   ```bash
   python app/app_new.py
   # Verify your devices and reviews are present
   ```

## Troubleshooting

### SSH Connection Issues

**Error**: "Authentication failed"
- Ensure SSH keys are properly installed on pfSense device
- Verify SSH username is correct
- Check SSH key permissions (should be 600)

**Error**: "Host key verification failed"
- If testing: Set `SSH_KNOWN_HOSTS_CHECK=False` in `.env`
- If production: Add pfSense host key to `~/.ssh/known_hosts`

### Auto-Check Issues

**Error**: "Cannot read /conf/config.xml"
- Verify SSH user has permissions to read config.xml
- Most pfSense users (admin, root) have access

**Controls show "Not Reviewed"**
- Check logs for specific error messages
- Verify network connectivity to management IP
- Ensure pfSense SSH service is running

### Database Issues

**Error**: "Database is locked"
- Only one process should access the database
- Close other instances of the application

## Contributing

Contributions welcome! Please:

1. Follow existing code style (PEP 8)
2. Add type hints to new functions
3. Write unit tests for new features
4. Update documentation

## License

[Add your license here]

## Changelog

### v2.0 (Refactored)

- ✅ Fixed all security vulnerabilities
- ✅ Modular architecture
- ✅ Comprehensive logging
- ✅ Unit tests
- ✅ Configuration management
- ✅ Error handling
- ✅ Type hints throughout
- ✅ Authentication system
- ✅ Timezone-aware timestamps
- ✅ Data-driven check system

### v1.0 (Original)

- Initial release
- Basic device management
- Manual compliance tracking
- Automated SSH checks
- CSV export

## Support

For issues, please check:
1. The Troubleshooting section above
2. Application logs (when running with logging enabled)
3. GitHub issues (if applicable)
