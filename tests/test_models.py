"""
Unit tests for models module.
"""

import unittest
import tempfile
import os
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models import Database, ComplianceStatus


class TestComplianceStatus(unittest.TestCase):
    """Tests for ComplianceStatus enum."""

    def test_from_string_valid(self):
        """Test converting valid strings to enum."""
        self.assertEqual(
            ComplianceStatus.from_string("Compliant"),
            ComplianceStatus.COMPLIANT
        )
        self.assertEqual(
            ComplianceStatus.from_string("Non Compliant"),
            ComplianceStatus.NON_COMPLIANT
        )

    def test_from_string_invalid(self):
        """Test converting invalid strings defaults to NOT_REVIEWED."""
        self.assertEqual(
            ComplianceStatus.from_string("Invalid"),
            ComplianceStatus.NOT_REVIEWED
        )

    def test_str_conversion(self):
        """Test string conversion."""
        self.assertEqual(
            str(ComplianceStatus.COMPLIANT),
            "Compliant"
        )


class TestDatabase(unittest.TestCase):
    """Tests for Database class."""

    def setUp(self):
        """Create a temporary database for testing."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db = Database(self.temp_db.name)
        self.db.init_db()

    def tearDown(self):
        """Clean up temporary database."""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_create_device(self):
        """Test creating a device."""
        device_id = self.db.create_device(
            name="Test Device",
            hostname="test.local",
            notes="Test notes",
            mgmt_ip="192.168.1.1",
            ssh_user="admin"
        )
        self.assertIsInstance(device_id, int)
        self.assertGreater(device_id, 0)

    def test_get_device(self):
        """Test retrieving a device."""
        device_id = self.db.create_device(
            name="Test Device",
            hostname="test.local",
            notes="Test notes",
            mgmt_ip="192.168.1.1",
            ssh_user="admin"
        )

        device = self.db.get_device(device_id)
        self.assertIsNotNone(device)
        self.assertEqual(device["name"], "Test Device")
        self.assertEqual(device["hostname"], "test.local")
        self.assertEqual(device["mgmt_ip"], "192.168.1.1")

    def test_get_nonexistent_device(self):
        """Test retrieving a non-existent device."""
        device = self.db.get_device(9999)
        self.assertIsNone(device)

    def test_update_device(self):
        """Test updating a device."""
        device_id = self.db.create_device(
            name="Original Name",
            hostname="original.local",
            notes="",
            mgmt_ip="192.168.1.1",
            ssh_user="admin"
        )

        self.db.update_device(
            device_id,
            name="Updated Name",
            hostname="updated.local",
            notes="Updated notes",
            mgmt_ip="192.168.1.2",
            ssh_user="root"
        )

        device = self.db.get_device(device_id)
        self.assertEqual(device["name"], "Updated Name")
        self.assertEqual(device["hostname"], "updated.local")
        self.assertEqual(device["mgmt_ip"], "192.168.1.2")

    def test_delete_device(self):
        """Test deleting a device."""
        device_id = self.db.create_device(
            name="Test Device",
            hostname="test.local",
            notes="",
            mgmt_ip="192.168.1.1",
            ssh_user="admin"
        )

        self.db.delete_device_and_reviews(device_id)
        device = self.db.get_device(device_id)
        self.assertIsNone(device)

    def test_get_all_devices(self):
        """Test retrieving all devices."""
        self.db.create_device("Device 1", "", "", "192.168.1.1", "admin")
        self.db.create_device("Device 2", "", "", "192.168.1.2", "admin")

        devices = self.db.get_all_devices()
        self.assertEqual(len(devices), 2)
        self.assertEqual(devices[0]["name"], "Device 1")
        self.assertEqual(devices[1]["name"], "Device 2")

    def test_save_review(self):
        """Test saving a review."""
        device_id = self.db.create_device(
            "Test Device", "", "", "192.168.1.1", "admin"
        )

        self.db.save_review(
            device_id,
            item_index=0,
            status="Compliant",
            note="Test note"
        )

        reviews = self.db.get_reviews_for_device(device_id)
        self.assertIn(0, reviews)
        self.assertEqual(reviews[0]["status"], "Compliant")
        self.assertEqual(reviews[0]["note"], "Test note")

    def test_update_review(self):
        """Test updating an existing review."""
        device_id = self.db.create_device(
            "Test Device", "", "", "192.168.1.1", "admin"
        )

        self.db.save_review(device_id, 0, "Compliant", "Original note")
        self.db.save_review(device_id, 0, "Non Compliant", "Updated note")

        reviews = self.db.get_reviews_for_device(device_id)
        self.assertEqual(reviews[0]["status"], "Non Compliant")
        self.assertEqual(reviews[0]["note"], "Updated note")

    def test_get_reviews_empty(self):
        """Test getting reviews for device with no reviews."""
        device_id = self.db.create_device(
            "Test Device", "", "", "192.168.1.1", "admin"
        )

        reviews = self.db.get_reviews_for_device(device_id)
        self.assertEqual(len(reviews), 0)


if __name__ == "__main__":
    unittest.main()
