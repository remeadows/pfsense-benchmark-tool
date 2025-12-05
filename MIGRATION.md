# Migration Guide: v1.0 → v2.0

This guide helps you migrate from the original `app.py` to the refactored `app_new.py`.

## Why Migrate?

The v2.0 refactor fixes **all 26 issues** identified in the code review:

### Critical Security Fixes
- ✅ XML parsing now uses `defusedxml` (prevents XXE attacks)
- ✅ SSH authentication is key-based only (no password storage)
- ✅ SQL injection risks eliminated
- ✅ HTTP authentication added (prevents unauthorized access)
- ✅ SSH host key verification (prevents MITM attacks)

### Code Quality Improvements
- ✅ Modular architecture (7 focused modules vs 1 monolithic file)
- ✅ Comprehensive logging system
- ✅ Type hints throughout
- ✅ Unit tests (20+ test cases)
- ✅ Proper error handling
- ✅ Configuration management

### Functionality Enhancements
- ✅ Timezone-aware timestamps
- ✅ Better CSV sanitization
- ✅ Data-driven check system
- ✅ Improved error messages

## Pre-Migration Checklist

- [ ] Backup your `reviews.db` database
- [ ] Backup your `pfsense_benchmark.json` or `.ckl` file
- [ ] Document your current admin credentials
- [ ] List all SSH-accessible devices
- [ ] Note any custom modifications to the original code

## Step-by-Step Migration

### 1. Backup Your Data

```bash
# Backup database
cp reviews.db reviews.db.backup

# Backup checklist
cp pfsense_benchmark.json pfsense_benchmark.json.backup
# or
cp pfsense_benchmark.ckl pfsense_benchmark.ckl.backup

# Backup original app (optional)
cp app/app.py app/app_old.py
```

### 2. Install New Dependencies

```bash
# Install required packages
pip install -r requirements.txt

# Verify installation
python -c "import defusedxml; print('defusedxml OK')"
python -c "import dotenv; print('python-dotenv OK')"
```

### 3. Set Up Environment Configuration

```bash
# Copy example env file
cp .env.example .env
```

Edit `.env` and configure:

```bash
# Generate a secure secret key
python -c "import secrets; print(secrets.token_hex(32))"
# Copy output to FLASK_SECRET_KEY

# Set authentication
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-password-here

# Production settings
FLASK_DEBUG=False
SSH_KNOWN_HOSTS_CHECK=True
SSH_TIMEOUT=30
```

### 4. Set Up SSH Keys

The new version uses **key-based authentication only** for security.

```bash
# Generate SSH key (if you don't have one)
ssh-keygen -t ed25519 -f ~/.ssh/pfsense_key -C "pfsense-benchmark-tool"

# Copy to each pfSense device
ssh-copy-id -i ~/.ssh/pfsense_key.pub admin@<pfsense-ip>

# Test connection
ssh -i ~/.ssh/pfsense_key admin@<pfsense-ip> "echo Connection OK"
```

**Important**: Update your SSH agent or ssh config:

```bash
# Add to ~/.ssh/config
Host pfsense-*
    IdentityFile ~/.ssh/pfsense_key
    User admin
```

### 5. Update Device Records

The new version **does not store SSH passwords**. You'll need to ensure:

1. All devices have SSH key authentication set up
2. The `ssh_user` field is populated for each device
3. Remove any SSH password fields (they're ignored anyway)

You can verify this in the web interface after starting the app.

### 6. Test Database Compatibility

The database schema is backward compatible, but let's verify:

```bash
python -c "
from app.models import Database
db = Database('reviews.db')
devices = db.get_all_devices()
print(f'Found {len(devices)} devices')
for d in devices:
    print(f\"  - {d['name']}: {d.get('mgmt_ip', 'No IP')}\")
"
```

Expected output: List of your devices

### 7. Start the New Application

```bash
cd app
python app_new.py
```

You should see:
```
INFO - Loaded 150 checklist items
INFO - Database initialized successfully
 * Running on http://127.0.0.1:5000
```

### 8. Verify Migration

1. **Login**: Use credentials from `.env`
   - URL: `http://localhost:5000`
   - Enter username/password when prompted

2. **Check Devices**:
   - Navigate to Devices page
   - Verify all devices are listed
   - Edit each device to ensure `mgmt_ip` and `ssh_user` are set

3. **Test Auto-Check**:
   - Select a device
   - Click "Run Auto-Checks"
   - Verify checks complete without errors

4. **Check Reviews**:
   - Open a device checklist
   - Verify existing review statuses are preserved
   - Check that notes are intact

5. **Export Test**:
   - Export a device to CSV
   - Verify filename is sanitized
   - Check timestamp is included

## Troubleshooting

### Issue: "Authentication Required" popup won't accept credentials

**Cause**: Browser cached old session or incorrect credentials

**Fix**:
1. Clear browser cache
2. Try incognito/private window
3. Verify credentials in `.env` match what you're entering
4. Check if password has special characters - escape them in `.env`

### Issue: "Authentication failed" during auto-check

**Cause**: SSH keys not set up properly

**Fix**:
```bash
# Test SSH manually
ssh -i ~/.ssh/pfsense_key admin@<pfsense-ip>

# If that fails, re-copy keys
ssh-copy-id -i ~/.ssh/pfsense_key.pub admin@<pfsense-ip>

# Verify key permissions
chmod 600 ~/.ssh/pfsense_key
chmod 644 ~/.ssh/pfsense_key.pub
```

### Issue: "Host key verification failed"

**Cause**: SSH host key not in known_hosts

**Fix Option 1** (Secure - Recommended):
```bash
# Add host key manually
ssh-keyscan -H <pfsense-ip> >> ~/.ssh/known_hosts
```

**Fix Option 2** (Testing only):
```bash
# Disable host key checking in .env
SSH_KNOWN_HOSTS_CHECK=False
```

### Issue: Old checks.py file conflicts

**Cause**: Original `checks.py` imported somewhere

**Fix**:
```bash
# The new version doesn't use checks.py
# It's safe to rename or delete it
mv app/checks.py app/checks_old.py
```

### Issue: Import errors for new modules

**Cause**: Python can't find the app module

**Fix**:
```bash
# Ensure you're in the correct directory
cd /path/to/Pfsense_Benchmark_Tool

# Run from app directory
cd app
python app_new.py

# Or use module syntax
python -m app.app_new
```

### Issue: defusedxml not found

**Cause**: Requirements not installed

**Fix**:
```bash
pip install -r requirements.txt

# If using virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Rollback Procedure

If you need to rollback to the original version:

```bash
# Stop the new app (Ctrl+C)

# Restore database backup
cp reviews.db.backup reviews.db

# Run old app
cd app
python app_old.py  # or app.py if you didn't rename it
```

## Post-Migration Tasks

### 1. Update Deployment Scripts

If you have deployment scripts, update them:

```bash
# Old
python app/app.py

# New
cd app && python app_new.py
# or with gunicorn
gunicorn -w 4 'app.app_new:app'
```

### 2. Update Documentation

Update any internal documentation referencing:
- File paths
- Module imports
- Configuration methods
- SSH authentication process

### 3. Train Users

Key changes users will notice:
- **Login required**: They'll need to authenticate
- **No password storage**: SSH keys must be set up
- **Better error messages**: More informative feedback
- **Timezone in timestamps**: CSV exports include UTC timestamps

### 4. Monitor Logs

The new version has comprehensive logging:

```bash
# Watch logs in real-time
tail -f /var/log/pfsense-benchmark.log  # if configured

# Or use systemd journal
journalctl -u pfsense-benchmark -f
```

### 5. Schedule Regular Checks

Consider automating compliance checks:

```bash
# Example cron job to run checks weekly
0 2 * * 0 /path/to/run-checks.sh
```

## Performance Notes

The refactored version:
- **Faster**: Connection pooling and better queries
- **More secure**: But SSH key checks add slight overhead
- **Better error recovery**: Retries and timeouts

Expected auto-check times:
- Original: ~30-45 seconds per device
- Refactored: ~25-35 seconds per device (with SFTP)

## Getting Help

If you encounter issues:

1. Check the application logs
2. Review this migration guide
3. Check `README.md` for general usage
4. Review `TROUBLESHOOTING.md` (if available)
5. File an issue on GitHub (if applicable)

## Validation Checklist

After migration, verify:

- [ ] All devices are accessible
- [ ] Existing reviews are preserved
- [ ] Auto-checks complete successfully
- [ ] CSV exports work
- [ ] Reports generate correctly
- [ ] Authentication works
- [ ] SSH key authentication works
- [ ] No errors in logs

## Next Steps

Once migrated successfully:

1. **Remove old code**:
   ```bash
   rm app/app.py  # or keep as app_old.py for reference
   mv app/app_new.py app/app.py
   ```

2. **Set up production server** (see README.md)

3. **Configure automated backups** for `reviews.db`

4. **Set up monitoring** for the application

5. **Run unit tests periodically**:
   ```bash
   python -m unittest discover tests
   ```

## FAQ

**Q: Can I run both versions simultaneously?**

A: Yes, use different ports:
```bash
# Old version
python app/app.py  # runs on 5000

# New version (in another terminal)
python app/app_new.py  # also runs on 5000 - will conflict
```

Change port in code or use different databases.

**Q: Will my existing CKL files work?**

A: Yes! The new parser is backward compatible with CKL files.

**Q: Do I need to re-run all compliance checks?**

A: No, existing review data is preserved. But you may want to re-run auto-checks to verify the new SSH implementation works.

**Q: What about custom modifications to app.py?**

A: Review your modifications and:
1. Map them to the appropriate new module
2. Apply changes following the new architecture
3. Add unit tests for custom logic

**Q: Is the API the same?**

A: The web interface is identical. Internal APIs changed significantly (now modular).

## Success!

Once you see this, you've successfully migrated:

```
✓ Application starts without errors
✓ Login works
✓ Devices are visible
✓ Reviews are preserved
✓ Auto-checks complete
✓ Exports work
✓ No security warnings
```

Congratulations! You're now running the secure, refactored version.
