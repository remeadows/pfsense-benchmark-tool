# GitHub Repository Setup Guide

Complete guide to setting up your pfSense Benchmark Tool repository on GitHub.

## Step 1: Create GitHub Repository

### Option A: Via GitHub Web Interface

1. Go to https://github.com/new
2. Fill in repository details:
   - **Repository name**: `pfsense-benchmark-tool`
   - **Description**: "A Flask web application for conducting pfSense CIS/STIG security benchmark assessments"
   - **Visibility**: Choose Public or Private
   - **DO NOT** initialize with README (we already have one)
   - **DO NOT** add .gitignore or license (we have them)
3. Click **"Create repository"**

### Option B: Via GitHub CLI

```bash
gh repo create pfsense-benchmark-tool --public --description "A Flask web application for conducting pfSense CIS/STIG security benchmark assessments"
```

## Step 2: Initialize Git (if not already done)

```bash
cd C:\Users\rmeadows\Projects\dev\Pfsense_Benchmark_Tool

# Initialize git repository
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: pfSense Benchmark Tool v2.0"
```

## Step 3: Connect to GitHub

```bash
# Add remote (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/pfsense-benchmark-tool.git

# Verify remote
git remote -v

# Push to GitHub
git branch -M main
git push -u origin main
```

## Step 4: Configure Repository Settings

### A. General Settings

1. Go to **Settings** → **General**
2. **Features**:
   - ✅ Issues
   - ✅ Discussions (optional)
   - ✅ Projects (optional)
   - ✅ Wiki (optional)
3. **Pull Requests**:
   - ✅ Allow squash merging
   - ✅ Automatically delete head branches
4. **Save changes**

### B. Branch Protection Rules

1. Go to **Settings** → **Branches**
2. Click **"Add rule"**
3. **Branch name pattern**: `main`
4. Enable:
   - ✅ Require a pull request before merging
   - ✅ Require approvals (1 minimum)
   - ✅ Dismiss stale pull request approvals
   - ✅ Require status checks to pass
   - ✅ Require branches to be up to date
   - ✅ Require conversation resolution
5. **Save changes**

### C. Security Settings

1. Go to **Settings** → **Security** → **Code security and analysis**
2. Enable:
   - ✅ Dependency graph
   - ✅ Dependabot alerts
   - ✅ Dependabot security updates
   - ✅ Code scanning (optional)
   - ✅ Secret scanning
3. **Configure Dependabot**:
   - Will auto-create PRs for dependency updates

### D. Enable GitHub Actions

GitHub Actions will run automatically based on the workflow files in `.github/workflows/`.

Workflows included:
- **ci.yml**: Runs tests on every push/PR
- **release.yml**: Creates releases for tags

## Step 5: Set Up Secrets (if needed)

If you plan to publish to PyPI or need other secrets:

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Click **"New repository secret"**
3. Add secrets:
   - `PYPI_API_TOKEN` (if publishing to PyPI)
   - Others as needed

## Step 6: Create Initial Release

### Option A: Via GitHub Web Interface

1. Go to **Releases** → **"Create a new release"**
2. **Tag version**: `v2.0.0`
3. **Release title**: `v2.0.0 - Complete Refactor`
4. **Description**: Copy from CHANGELOG.md
5. Attach files: requirements.txt, README.md, etc.
6. Click **"Publish release"**

### Option B: Via Git Tag

```bash
# Create annotated tag
git tag -a v2.0.0 -m "Release v2.0.0 - Complete Refactor"

# Push tag to GitHub
git push origin v2.0.0
```

The release.yml workflow will automatically create a GitHub release.

## Step 7: Configure Issue Templates

Issue templates are already created in `.github/ISSUE_TEMPLATE/`:
- Bug Report
- Feature Request
- Security Vulnerability

They will appear automatically when users create issues.

## Step 8: Add Repository Topics

1. Go to repository main page
2. Click **"Add topics"**
3. Add relevant topics:
   - `pfsense`
   - `security`
   - `compliance`
   - `stig`
   - `cis-benchmark`
   - `flask`
   - `python`
   - `audit-tool`
   - `network-security`
   - `firewall`

## Step 9: Create README Badges

Add these badges to the top of your README.md:

```markdown
# pfSense Benchmark Tool

[![CI](https://github.com/YOUR_USERNAME/pfsense-benchmark-tool/workflows/CI/badge.svg)](https://github.com/YOUR_USERNAME/pfsense-benchmark-tool/actions)
[![codecov](https://codecov.io/gh/YOUR_USERNAME/pfsense-benchmark-tool/branch/main/graph/badge.svg)](https://codecov.io/gh/YOUR_USERNAME/pfsense-benchmark-tool)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

[Rest of README...]
```

## Step 10: Set Up Codecov (Optional)

For code coverage reporting:

1. Go to https://codecov.io/
2. Sign in with GitHub
3. Add your repository
4. Copy the token
5. Add `CODECOV_TOKEN` to repository secrets
6. Coverage reports will be generated automatically by CI

## Step 11: Enable Discussions (Optional)

1. Go to **Settings** → **General**
2. Under **Features**, enable **Discussions**
3. Create categories:
   - **Q&A**: Questions and answers
   - **Ideas**: Feature suggestions
   - **Show and tell**: Share your setups
   - **General**: General discussion

## Step 12: Create Project Boards (Optional)

For tracking development:

1. Go to **Projects** → **New project**
2. Choose template (e.g., "Automated kanban")
3. Create boards:
   - **Backlog**: Future features
   - **To Do**: Planned for next release
   - **In Progress**: Currently working on
   - **Done**: Completed

## File Structure Summary

Your repository now includes:

```
.
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                    # CI/CD pipeline
│   │   └── release.yml               # Release automation
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   ├── feature_request.md
│   │   └── security_vulnerability.md
│   └── PULL_REQUEST_TEMPLATE.md
├── app/                               # Application code
├── tests/                             # Unit tests
├── scripts/                           # Utility scripts
├── .env.example                       # Environment config template
├── .gitignore                         # Git ignore rules
├── requirements.txt                   # Python dependencies
├── README.md                          # Main documentation
├── QUICKSTART.md                      # Quick start guide
├── MIGRATION.md                       # Migration guide
├── CONTRIBUTING.md                    # Contribution guidelines
├── CHANGELOG.md                       # Version history
├── REFACTORING_SUMMARY.md             # Technical details
├── GITHUB_SETUP.md                    # This file
└── LICENSE                            # MIT License
```

## Git Workflow

### Daily Development

```bash
# Create feature branch
git checkout -b feature/new-check

# Make changes
# ... edit files ...

# Stage and commit
git add .
git commit -m "feat: Add new compliance check for XYZ"

# Push to GitHub
git push origin feature/new-check

# Create pull request via GitHub web interface
```

### Keeping Fork Updated

```bash
# Add upstream remote (if you forked)
git remote add upstream https://github.com/ORIGINAL_OWNER/pfsense-benchmark-tool.git

# Fetch upstream changes
git fetch upstream

# Merge into main
git checkout main
git merge upstream/main

# Push to your fork
git push origin main
```

### Release Process

```bash
# Update CHANGELOG.md with new version

# Commit changes
git add CHANGELOG.md
git commit -m "chore: Prepare v2.1.0 release"

# Create tag
git tag -a v2.1.0 -m "Release v2.1.0"

# Push tag
git push origin v2.1.0

# GitHub Actions will automatically create release
```

## Common Tasks

### Update Dependencies

```bash
# Update requirements.txt
pip list --outdated
pip install --upgrade <package>
pip freeze > requirements.txt

# Commit
git add requirements.txt
git commit -m "chore: Update dependencies"
```

### Run CI Locally

```bash
# Install act (GitHub Actions locally)
# Windows: choco install act
# Mac: brew install act
# Linux: Check https://github.com/nektos/act

# Run CI locally
act push
```

### Fix Failed CI

```bash
# Pull latest
git pull origin main

# Run tests locally
python -m pytest tests/ -v

# Fix issues
# ... make changes ...

# Push fix
git add .
git commit -m "fix: Resolve CI test failures"
git push
```

## Troubleshooting

### Push Rejected

```bash
# If push rejected, pull first
git pull origin main --rebase

# Resolve conflicts if any
# ... fix conflicts ...
git add .
git rebase --continue

# Push again
git push origin main
```

### Large Files

If you accidentally commit large files:

```bash
# Install git-filter-repo
pip install git-filter-repo

# Remove large file from history
git filter-repo --path path/to/large-file --invert-paths

# Force push (use with caution!)
git push origin main --force
```

### Sensitive Data Committed

1. **Immediately** change any exposed credentials
2. Use git-filter-repo to remove from history
3. Consider the repository compromised if public

## Best Practices

1. **Never commit**:
   - `.env` files with real credentials
   - `*.db` database files with real data
   - SSH keys
   - Excel files with sensitive info

2. **Always**:
   - Write clear commit messages
   - Test before pushing
   - Update documentation
   - Review your own PRs

3. **For Security**:
   - Enable 2FA on GitHub
   - Use SSH keys for git operations
   - Review dependency updates
   - Monitor security alerts

## Next Steps

1. ✅ Repository created
2. ✅ Code pushed
3. ✅ Settings configured
4. ✅ CI/CD enabled
5. ✅ Issue templates ready
6. ⬜ Create first release
7. ⬜ Add badges to README
8. ⬜ Set up Codecov (optional)
9. ⬜ Enable Discussions (optional)
10. ⬜ Share with community!

## Resources

- [GitHub Docs](https://docs.github.com/)
- [GitHub Actions](https://docs.github.com/en/actions)
- [Git Book](https://git-scm.com/book/en/v2)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)

---

Your repository is now fully configured and ready for collaboration! 🚀
