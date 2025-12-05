"""
Unit tests for reports module.
"""

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.reports import compute_device_summary, build_device_items
from app.models import ComplianceStatus


class TestComputeDeviceSummary(unittest.TestCase):
    """Tests for compute_device_summary function."""

    def setUp(self):
        """Set up test data."""
        self.checklist_items = [
            {
                "section": "Section 1",
                "control_id": "1.1",
                "title": "Test 1",
                "status": "Not Reviewed",
            },
            {
                "section": "Section 1",
                "control_id": "1.2",
                "title": "Test 2",
                "status": "Compliant",
            },
            {
                "section": "Section 2",
                "control_id": "2.1",
                "title": "Test 3",
                "status": "Non Compliant",
            },
            {
                "section": "Section 2",
                "control_id": "2.2",
                "title": "Test 4",
                "status": "Non Applicable",
            },
        ]

    def test_all_default_status(self):
        """Test summary with no review overrides."""
        reviews = {}
        summary = compute_device_summary(self.checklist_items, reviews)

        self.assertEqual(summary["total_items"], 4)
        self.assertEqual(summary["reviewed"], 3)
        self.assertEqual(summary["not_reviewed"], 1)
        self.assertEqual(summary["compliant"], 1)
        self.assertEqual(summary["non_compliant"], 1)
        self.assertEqual(summary["non_applicable"], 1)

    def test_with_review_overrides(self):
        """Test summary with review overrides."""
        reviews = {
            0: {"status": "Compliant", "note": "Reviewed and compliant"},
            2: {"status": "Compliant", "note": "Fixed"},
        }
        summary = compute_device_summary(self.checklist_items, reviews)

        self.assertEqual(summary["reviewed"], 4)
        self.assertEqual(summary["not_reviewed"], 0)
        self.assertEqual(summary["compliant"], 3)
        self.assertEqual(summary["non_compliant"], 0)

    def test_compliance_percentage(self):
        """Test compliance percentage calculation."""
        reviews = {
            0: {"status": "Compliant", "note": ""},
            1: {"status": "Compliant", "note": ""},
            2: {"status": "Non Compliant", "note": ""},
            3: {"status": "Non Applicable", "note": ""},
        }
        summary = compute_device_summary(self.checklist_items, reviews)

        # 2 compliant + 1 non-applicable = 3 out of 4 = 75%
        self.assertEqual(summary["compliance_pct"], 75.0)

    def test_section_non_compliant(self):
        """Test section-wise non-compliant tracking."""
        reviews = {
            0: {"status": "Non Compliant", "note": ""},
            2: {"status": "Non Compliant", "note": ""},
        }
        summary = compute_device_summary(self.checklist_items, reviews)

        self.assertEqual(summary["section_non_compliant"]["Section 1"], 1)
        self.assertEqual(summary["section_non_compliant"]["Section 2"], 1)


class TestBuildDeviceItems(unittest.TestCase):
    """Tests for build_device_items function."""

    def setUp(self):
        """Set up test data."""
        self.checklist_items = [
            {
                "section": "Section 1",
                "control_id": "1.1",
                "title": "Test 1",
                "status": "Not Reviewed",
                "comment": "Base comment",
            },
            {
                "section": "Section 1",
                "control_id": "1.2",
                "title": "Test 2",
                "status": "Compliant",
                "comment": "",
            },
        ]

    def test_no_reviews(self):
        """Test building items with no reviews."""
        reviews = {}
        items = build_device_items(self.checklist_items, reviews)

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["status"], "Not Reviewed")
        self.assertEqual(items[0]["comment"], "")  # Base comments ignored
        self.assertEqual(items[1]["status"], "Compliant")

    def test_with_reviews(self):
        """Test building items with review overrides."""
        reviews = {
            0: {"status": "Compliant", "note": "Device-specific note"},
            1: {"status": "Non Compliant", "note": "Issue found"},
        }
        items = build_device_items(self.checklist_items, reviews)

        self.assertEqual(items[0]["status"], "Compliant")
        self.assertEqual(items[0]["comment"], "Device-specific note")
        self.assertEqual(items[1]["status"], "Non Compliant")
        self.assertEqual(items[1]["comment"], "Issue found")

    def test_index_added(self):
        """Test that index is added to items."""
        reviews = {}
        items = build_device_items(self.checklist_items, reviews)

        self.assertEqual(items[0]["index"], 0)
        self.assertEqual(items[1]["index"], 1)


if __name__ == "__main__":
    unittest.main()
