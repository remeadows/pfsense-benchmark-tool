# Contributing to pfSense Benchmark Tool

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Features](#suggesting-features)

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on what is best for the community
- Show empathy towards other community members

### Unacceptable Behavior

- Harassment or discriminatory language
- Trolling or insulting comments
- Publishing others' private information
- Other conduct inappropriate in a professional setting

## Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/pfsense-benchmark-tool.git
   cd pfsense-benchmark-tool
   ```
3. Add upstream remote:
   ```bash
   git remote add upstream https://github.com/ORIGINAL_OWNER/pfsense-benchmark-tool.git
   ```

## Development Setup

### Prerequisites

- Python 3.10 or higher
- Git
- A pfSense device for testing (recommended but not required)

### Environment Setup

1. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # If exists
   ```

3. **Install development tools**:
   ```bash
   pip install pytest pytest-cov flake8 black mypy bandit isort
   ```

4. **Set up environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your test configuration
   ```

5. **Run tests to verify setup**:
   ```bash
   python -m pytest tests/ -v
   ```

## How to Contribute

### Types of Contributions

1. **Bug Fixes** - Fix identified issues
2. **New Features** - Add new functionality
3. **Documentation** - Improve docs, add examples
4. **Tests** - Increase test coverage
5. **Code Quality** - Refactoring, performance improvements

### Contribution Workflow

1. **Create a branch**:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

2. **Make your changes**:
   - Write code
   - Add tests
   - Update documentation

3. **Test your changes**:
   ```bash
   python -m pytest tests/ -v
   flake8 app/
   mypy app/
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "Add feature: description of feature"
   ```

5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request**:
   - Go to GitHub
   - Click "New Pull Request"
   - Fill out the PR template

## Coding Standards

### Python Style Guide

Follow PEP 8 with these specifics:

- **Line Length**: 100 characters max
- **Indentation**: 4 spaces (no tabs)
- **Quotes**: Use double quotes for strings
- **Imports**: Group by standard library, third-party, local

### Code Formatting

We use **Black** for code formatting:

```bash
black app/ tests/
```

### Import Sorting

We use **isort** for import sorting:

```bash
isort app/ tests/
```

### Type Hints

Use type hints for all function signatures:

```python
def create_device(
    name: str,
    hostname: str,
    notes: str,
    mgmt_ip: str,
    ssh_user: str
) -> int:
    """Create a new device."""
    ...
```

### Docstrings

Use Google-style docstrings:

```python
def compute_summary(items: list[dict], reviews: dict) -> dict:
    """
    Compute compliance summary for a device.

    Args:
        items: List of checklist items
        reviews: Device-specific reviews

    Returns:
        Dictionary containing summary statistics

    Raises:
        ValueError: If items list is empty
    """
    ...
```

### Naming Conventions

- **Functions/Variables**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private methods**: `_leading_underscore`

### Security Best Practices

1. **Never commit secrets** (use .env files)
2. **Validate all input** from users and external sources
3. **Use parameterized queries** for database operations
4. **Sanitize file paths** and filenames
5. **Log security events** appropriately

### Example Code Style

```python
from typing import Optional
import logging

from .models import Database, ComplianceStatus

logger = logging.getLogger(__name__)


class DeviceManager:
    """Manages device operations."""

    def __init__(self, db: Database):
        """
        Initialize device manager.

        Args:
            db: Database instance
        """
        self.db = db
        logger.info("DeviceManager initialized")

    def get_device(self, device_id: int) -> Optional[dict]:
        """
        Retrieve a device by ID.

        Args:
            device_id: Device database ID

        Returns:
            Device dictionary or None if not found
        """
        logger.debug(f"Fetching device {device_id}")
        device = self.db.get_device(device_id)

        if device is None:
            logger.warning(f"Device {device_id} not found")
            return None

        return device
```

## Testing

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=app --cov-report=html

# Run specific test file
python -m pytest tests/test_models.py -v

# Run specific test
python -m pytest tests/test_models.py::TestDatabase::test_create_device -v
```

### Writing Tests

Place tests in `tests/` directory with `test_` prefix:

```python
import unittest
from app.models import Database


class TestDatabase(unittest.TestCase):
    """Tests for Database class."""

    def setUp(self):
        """Set up test fixtures."""
        self.db = Database(":memory:")
        self.db.init_db()

    def test_create_device(self):
        """Test device creation."""
        device_id = self.db.create_device(
            "Test Device", "test.local", "", "192.168.1.1", "admin"
        )
        self.assertIsInstance(device_id, int)
        self.assertGreater(device_id, 0)

    def tearDown(self):
        """Clean up after tests."""
        pass
```

### Test Coverage Goals

- **Minimum**: 70% coverage for new code
- **Target**: 80% coverage overall
- **Critical paths**: 100% coverage (auth, database, security)

## Pull Request Process

### Before Submitting

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] Added tests for new features
- [ ] Updated documentation
- [ ] No new linting errors
- [ ] Commit messages are clear

### PR Title Format

Use conventional commits format:

- `feat: Add new auto-check for firewall rules`
- `fix: Resolve SSH timeout issue`
- `docs: Update installation instructions`
- `test: Add tests for report generation`
- `refactor: Simplify database queries`
- `chore: Update dependencies`

### PR Description

Fill out the PR template completely:

1. **Description**: What and why
2. **Type of Change**: Bug fix, feature, etc.
3. **Testing**: How you tested
4. **Checklist**: Complete all items
5. **Screenshots**: If UI changes

### Review Process

1. **Automated checks** must pass (CI/CD)
2. **Code review** by at least one maintainer
3. **Address feedback** from reviewers
4. **Squash commits** if requested
5. **Maintainer merges** when approved

## Reporting Bugs

### Before Reporting

1. **Search existing issues** to avoid duplicates
2. **Try latest version** to see if fixed
3. **Gather information**:
   - OS and Python version
   - pfSense version
   - Tool version
   - Error messages/logs
   - Steps to reproduce

### Bug Report Template

Use the bug report issue template and include:

- Clear title
- Description of bug
- Steps to reproduce
- Expected vs actual behavior
- Environment details
- Log output
- Screenshots if applicable

### Security Vulnerabilities

**DO NOT** create public issues for security vulnerabilities.

Instead:
1. Use GitHub Security Advisories (private)
2. Or email security contact (if provided)
3. Include detailed information
4. Allow time for patch before disclosure

## Suggesting Features

### Feature Request Template

Use the feature request issue template:

1. **Problem statement**: What problem does this solve?
2. **Proposed solution**: How should it work?
3. **Alternatives**: Other approaches considered
4. **Use case**: How would you use it?
5. **Implementation ideas**: Technical approach

### Feature Discussion

- Discuss in issues before implementing
- Get maintainer feedback
- Consider impact on existing users
- Document breaking changes

## Project Structure

```
pfsense-benchmark-tool/
├── app/                    # Main application code
│   ├── __init__.py
│   ├── app_new.py         # Flask application
│   ├── models.py          # Database models
│   ├── parsers.py         # File parsers
│   ├── ssh_client.py      # SSH operations
│   ├── auth.py            # Authentication
│   ├── auto_checks.py     # Compliance checks
│   ├── reports.py         # Report generation
│   ├── config.py          # Configuration
│   └── templates/         # HTML templates
├── tests/                 # Unit tests
│   ├── test_models.py
│   └── test_reports.py
├── scripts/               # Utility scripts
│   └── parse_benchmark.py
├── .github/               # GitHub configuration
│   ├── workflows/         # CI/CD
│   └── ISSUE_TEMPLATE/    # Issue templates
├── docs/                  # Additional documentation (if needed)
├── requirements.txt       # Python dependencies
├── .env.example          # Example environment config
├── .gitignore            # Git ignore rules
├── README.md             # Main documentation
├── CONTRIBUTING.md       # This file
├── CHANGELOG.md          # Version history
└── LICENSE               # License file
```

## Getting Help

- **Documentation**: Read [README.md](README.md) and [QUICKSTART.md](QUICKSTART.md)
- **Issues**: Search existing issues
- **Discussions**: Use GitHub Discussions for questions
- **Email**: Contact maintainers (if provided)

## Recognition

Contributors are recognized in:
- GitHub contributors list
- CHANGELOG.md for significant contributions
- README.md for major features

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (see [LICENSE](LICENSE) file).

---

**Thank you for contributing to the pfSense Benchmark Tool!**
