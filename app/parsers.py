"""
Secure parsers for CKL and JSON checklist files.
Uses defusedxml to prevent XML vulnerabilities.
"""

import json
import logging
from pathlib import Path
from typing import Any
from defusedxml import ElementTree as ET

logger = logging.getLogger(__name__)


def load_ckl_items(path: Path) -> list[dict[str, Any]]:
    """
    Load checklist items from a DISA-style CKL file.
    Converts STIG fields to the structure the app expects.

    Args:
        path: Path to the CKL file

    Returns:
        List of checklist items

    Raises:
        FileNotFoundError: If CKL file doesn't exist
        ValueError: If CKL structure is invalid
    """
    if not path.exists():
        raise FileNotFoundError(f"CKL file not found: {path}")

    logger.info(f"Loading CKL items from {path}")

    try:
        root = ET.parse(str(path)).getroot()
    except ET.ParseError as e:
        raise ValueError(f"Invalid XML in CKL file: {e}")

    istig = root.find(".//STIGS/iSTIG")
    if istig is None:
        raise ValueError("No <iSTIG> block found in CKL.")

    STATUS_MAP = {
        "NotAFinding": "Compliant",
        "Open": "Non Compliant",
        "Not_Applicable": "Non Applicable",
        "Not_Reviewed": "Not Reviewed",
    }

    items = []
    for idx, vuln in enumerate(istig.findall("VULN")):
        stig_data = {}
        for sd in vuln.findall("STIG_DATA"):
            key = (sd.findtext("VULN_ATTRIBUTE") or "").strip()
            val = (sd.findtext("ATTRIBUTE_DATA") or "").strip()
            if key:
                stig_data[key] = val

        # Extract control ID
        raw_control = stig_data.get("Rule_ID") or stig_data.get("Vuln_Num") or ""
        control_id = raw_control[3:] if raw_control.upper().startswith("PF-") else raw_control
        control_id = control_id.strip() or f"item-{idx+1}"

        # Extract section from group title
        group_title = stig_data.get("Group_Title", "").strip()
        section = group_title.split(" - ")[0].strip() if " - " in group_title else group_title
        section = section or "Unknown"

        # Map status
        status_raw = (vuln.findtext("STATUS") or "Not_Reviewed").strip()
        status = STATUS_MAP.get(status_raw, "Not Reviewed")

        # Get comment from finding details or comments field
        comment = (
            (vuln.findtext("FINDING_DETAILS") or "").strip()
            or (vuln.findtext("COMMENTS") or "").strip()
        )

        items.append({
            "section": section,
            "control_id": control_id,
            "title": (stig_data.get("Rule_Title") or "").strip(),
            "rationale": (stig_data.get("Vuln_Discuss") or "").strip(),
            "fix_text": (stig_data.get("Fix_Text") or "").strip(),
            "status": status,
            "comment": comment,
            "row_index": idx,
        })

    if not items:
        raise ValueError("No VULN entries parsed from CKL.")

    logger.info(f"Loaded {len(items)} items from CKL")
    return items


def load_json_items(path: Path) -> list[dict[str, Any]]:
    """
    Load checklist items from legacy JSON format.

    Args:
        path: Path to the JSON file

    Returns:
        List of checklist items

    Raises:
        FileNotFoundError: If JSON file doesn't exist
        ValueError: If JSON is invalid
    """
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")

    logger.info(f"Loading JSON items from {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            items = json.load(f)

        if not isinstance(items, list):
            raise ValueError("JSON file must contain a list of items")

        logger.info(f"Loaded {len(items)} items from JSON")
        return items

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")


def load_checklist_items(ckl_path: Path, json_path: Path) -> list[dict[str, Any]]:
    """
    Load checklist items, preferring CKL over JSON.

    Args:
        ckl_path: Path to CKL file
        json_path: Path to JSON file (fallback)

    Returns:
        List of checklist items
    """
    if ckl_path.exists():
        try:
            return load_ckl_items(ckl_path)
        except Exception as e:
            logger.warning(f"Failed loading CKL ({ckl_path}): {e}. Falling back to JSON.")

    return load_json_items(json_path)


def parse_config_xml(xml_data: str) -> ET.Element:
    """
    Safely parse pfSense config.xml using defusedxml.

    Args:
        xml_data: XML content as string

    Returns:
        Root element of parsed XML

    Raises:
        ValueError: If XML is invalid
    """
    try:
        return ET.fromstring(xml_data)
    except ET.ParseError as e:
        raise ValueError(f"Invalid pfSense config.xml: {e}")
