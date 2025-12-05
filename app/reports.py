"""
Report generation and summary calculations.
"""

import logging
from typing import Any
from .models import ComplianceStatus

logger = logging.getLogger(__name__)


def compute_device_summary(checklist_items: list[dict], reviews: dict[int, dict]) -> dict[str, Any]:
    """
    Compute compliance summary for a device.

    Args:
        checklist_items: List of all checklist items
        reviews: Device-specific review overrides (item_index -> {status, note})

    Returns:
        Dictionary containing summary statistics
    """
    total_items = len(checklist_items)

    status_counts = {
        ComplianceStatus.NOT_REVIEWED.value: 0,
        ComplianceStatus.COMPLIANT.value: 0,
        ComplianceStatus.NON_COMPLIANT.value: 0,
        ComplianceStatus.NON_APPLICABLE.value: 0,
    }

    section_non_compliant: dict[str, int] = {}

    for idx, base_item in enumerate(checklist_items):
        section = base_item.get("section", "Unknown")
        status = base_item.get("status", ComplianceStatus.NOT_REVIEWED.value)

        # Override with device-specific review if available
        if idx in reviews:
            status = reviews[idx]["status"]

        # Validate status
        if status not in status_counts:
            logger.warning(f"Invalid status '{status}' for item {idx}, defaulting to Not Reviewed")
            status = ComplianceStatus.NOT_REVIEWED.value

        status_counts[status] += 1

        # Track non-compliant items by section
        if status == ComplianceStatus.NON_COMPLIANT.value:
            section_non_compliant[section] = section_non_compliant.get(section, 0) + 1

    reviewed = total_items - status_counts[ComplianceStatus.NOT_REVIEWED.value]
    not_reviewed = status_counts[ComplianceStatus.NOT_REVIEWED.value]
    compliant = status_counts[ComplianceStatus.COMPLIANT.value]
    non_compliant = status_counts[ComplianceStatus.NON_COMPLIANT.value]
    non_applicable = status_counts[ComplianceStatus.NON_APPLICABLE.value]

    # Calculate compliance percentage
    # Only count reviewed items (excluding Not Reviewed)
    # Non Applicable items count as compliant
    compliance_pct = 0.0
    if total_items > 0:
        denom = reviewed if reviewed > 0 else total_items
        compliance_pct = ((compliant + non_applicable) / denom) * 100.0

    return {
        "total_items": total_items,
        "reviewed": reviewed,
        "not_reviewed": not_reviewed,
        "compliant": compliant,
        "non_compliant": non_compliant,
        "non_applicable": non_applicable,
        "compliance_pct": round(compliance_pct, 1),
        "status_counts": status_counts,
        "section_non_compliant": section_non_compliant,
    }


def build_device_items(checklist_items: list[dict], reviews: dict[int, dict]) -> list[dict]:
    """
    Build list of items for a device with per-device overrides.

    IMPORTANT: Ignores the benchmark's default comments and only shows
    per-device review notes.

    Args:
        checklist_items: Base checklist items
        reviews: Device-specific review overrides

    Returns:
        List of items with device-specific status and comments
    """
    items_for_view = []

    for idx, base_item in enumerate(checklist_items):
        item = dict(base_item)
        item["index"] = idx

        status = item.get("status", ComplianceStatus.NOT_REVIEWED.value)
        comment = ""  # per-device comments only

        # Override with device-specific review
        if idx in reviews:
            status = reviews[idx]["status"]
            if reviews[idx]["note"]:
                comment = reviews[idx]["note"]

        item["status"] = status
        item["comment"] = comment
        items_for_view.append(item)

    return items_for_view
