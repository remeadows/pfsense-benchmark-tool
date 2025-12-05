"""
pfSense Benchmark Tool - Refactored Flask Application

A web application for conducting pfSense CIS/STIG security benchmark assessments.
"""

import logging
import re
import csv
import io
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from flask import (
    Flask,
    render_template,
    abort,
    request,
    redirect,
    url_for,
    Response,
)

from .config import Config
from .models import Database, ComplianceStatus
from .parsers import load_checklist_items, parse_config_xml
from .auth import AuthManager, requires_auth
from .reports import compute_device_summary, build_device_items
from .auto_checks import AutoChecker, CHECK_REGISTRY
from .ssh_client import SecureSSHClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY

# Initialize components
db = Database(str(Config.DB_PATH))
db.init_db()

auth_manager = AuthManager(Config.ADMIN_USERNAME, Config.ADMIN_PASSWORD)

# Load checklist items
try:
    checklist_items = load_checklist_items(Config.CKL_PATH, Config.JSON_PATH)
    logger.info(f"Loaded {len(checklist_items)} checklist items")
except Exception as e:
    logger.error(f"Failed to load checklist items: {e}")
    checklist_items = []

# Map control_id -> index for fast lookup
CONTROL_ID_TO_INDEX = {}
for idx, item in enumerate(checklist_items):
    cid = item.get("control_id")
    if cid:
        CONTROL_ID_TO_INDEX[cid.strip()] = idx


# -------------------------------------------------------------------
# Error Handlers
# -------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    return render_template(
        "error.html",
        error_code=404,
        error_message="Page not found",
        error_details="The requested resource could not be found."
    ), 404


@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {e}")
    return render_template(
        "error.html",
        error_code=500,
        error_message="Internal server error",
        error_details="An unexpected error occurred. Please try again."
    ), 500


# -------------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------------

def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing unsafe characters.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename safe for filesystem use
    """
    # Remove any character that's not alphanumeric, dash, underscore, or space
    safe_name = re.sub(r'[^\w\s-]', '', filename)
    # Replace spaces with underscores
    safe_name = safe_name.replace(' ', '_')
    # Remove multiple consecutive underscores
    safe_name = re.sub(r'_+', '_', safe_name)
    return safe_name


def run_auto_checks_ssh(device_id: int, device: dict) -> None:
    """
    Run automated checks via SSH.

    Args:
        device_id: Device database ID
        device: Device dictionary with mgmt_ip and ssh_user
    """
    mgmt_ip = (device.get("mgmt_ip") or "").strip()
    ssh_user = (device.get("ssh_user") or "").strip()

    if not mgmt_ip or not ssh_user:
        logger.warning(f"Device {device_id} missing mgmt_ip or ssh_user, skipping auto-checks")
        return

    logger.info(f"Running auto-checks for device {device_id} ({mgmt_ip})")

    try:
        with SecureSSHClient(
            mgmt_ip,
            ssh_user,
            timeout=Config.SSH_TIMEOUT,
            known_hosts_check=Config.SSH_KNOWN_HOSTS_CHECK
        ) as ssh_client:

            # Fetch config.xml using SFTP (safer than exec_command)
            xml_data = ssh_client.read_file("/conf/config.xml")

            if not xml_data:
                logger.error(f"Device {device_id}: Empty config.xml")
                _mark_control(device_id, "1.4", "Not Reviewed",
                             "Auto-check failed: empty config.xml")
                return

            # Parse config.xml securely
            config_root = parse_config_xml(xml_data)

            # Run all checks
            checker = AutoChecker(config_root, ssh_client)

            for control_id, check_func in CHECK_REGISTRY.items():
                try:
                    status, note = check_func(checker)
                    _mark_control(device_id, control_id, status, note)
                except Exception as e:
                    logger.error(f"Check {control_id} failed: {e}")
                    _mark_control(
                        device_id,
                        control_id,
                        "Not Reviewed",
                        f"Auto-check error: {type(e).__name__} - {e}"
                    )

            logger.info(f"Completed auto-checks for device {device_id}")

    except Exception as e:
        logger.error(f"Auto-check SSH error for device {device_id}: {e}")
        _mark_control(
            device_id,
            "1.4",
            "Not Reviewed",
            f"Auto-check SSH error: {type(e).__name__} - {e}"
        )


def _mark_control(device_id: int, control_id: str, status: str, note: str) -> None:
    """
    Mark a control with a specific status and note.

    Args:
        device_id: Device database ID
        control_id: Control identifier (e.g., "1.1")
        status: Compliance status
        note: Note explaining the status
    """
    idx = CONTROL_ID_TO_INDEX.get(control_id)
    if idx is None:
        logger.warning(f"Control ID {control_id} not found in checklist")
        return
    db.save_review(device_id, idx, status, note)


# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------

@app.route("/")
@requires_auth(auth_manager)
def index():
    """Redirect to devices list."""
    return redirect(url_for("devices"))


@app.route("/devices")
@requires_auth(auth_manager)
def devices():
    """Display all devices."""
    devices_list = db.get_all_devices()
    return render_template("devices.html", devices=devices_list)


@app.route("/devices/new", methods=["GET", "POST"])
@requires_auth(auth_manager)
def new_device():
    """Create a new device."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        hostname = request.form.get("hostname", "").strip()
        notes = request.form.get("notes", "").strip()
        mgmt_ip = request.form.get("mgmt_ip", "").strip()
        ssh_user = request.form.get("ssh_user", "").strip()

        if not name:
            return render_template(
                "error.html",
                error_code=400,
                error_message="Invalid Input",
                error_details="Device name is required."
            ), 400

        device_id = db.create_device(name, hostname, notes, mgmt_ip, ssh_user)
        return redirect(url_for("device_checklist", device_id=device_id))

    return render_template("device_form.html")


@app.route("/devices/<int:device_id>/edit", methods=["GET", "POST"])
@requires_auth(auth_manager)
def edit_device(device_id: int):
    """Edit an existing device."""
    device = db.get_device(device_id)
    if device is None:
        abort(404)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        hostname = request.form.get("hostname", "").strip()
        notes = request.form.get("notes", "").strip()
        mgmt_ip = request.form.get("mgmt_ip", "").strip()
        ssh_user = request.form.get("ssh_user", "").strip()

        if not name:
            return render_template(
                "error.html",
                error_code=400,
                error_message="Invalid Input",
                error_details="Device name is required."
            ), 400

        db.update_device(device_id, name, hostname, notes, mgmt_ip, ssh_user)
        return redirect(url_for("devices"))

    return render_template("device_edit.html", device=device)


@app.route("/devices/<int:device_id>/delete", methods=["POST"])
@requires_auth(auth_manager)
def delete_device_route(device_id: int):
    """Delete a device and its reviews."""
    device = db.get_device(device_id)
    if device is None:
        abort(404)

    db.delete_device_and_reviews(device_id)
    return redirect(url_for("devices"))


@app.route("/device/<int:device_id>/checklist")
@requires_auth(auth_manager)
def device_checklist(device_id: int):
    """Display device checklist."""
    device = db.get_device(device_id)
    if device is None:
        abort(404)

    reviews = db.get_reviews_for_device(device_id)
    items_for_view = build_device_items(checklist_items, reviews)
    summary = compute_device_summary(checklist_items, reviews)

    return render_template(
        "checklist.html",
        device=device,
        items=items_for_view,
        summary=summary,
    )


@app.route("/device/<int:device_id>/item/<int:item_index>", methods=["GET", "POST"])
@requires_auth(auth_manager)
def device_item_detail(device_id: int, item_index: int):
    """Display and update a specific checklist item."""
    device = db.get_device(device_id)
    if device is None:
        abort(404)

    if item_index < 0 or item_index >= len(checklist_items):
        abort(404)

    base_item = dict(checklist_items[item_index])
    reviews = db.get_reviews_for_device(device_id)

    status = base_item.get("status", ComplianceStatus.NOT_REVIEWED.value)
    comment = ""

    if item_index in reviews:
        status = reviews[item_index]["status"]
        if reviews[item_index]["note"]:
            comment = reviews[item_index]["note"]

    item = base_item
    item["status"] = status
    item["comment"] = comment
    item["row_index"] = base_item.get("row_index", item_index)

    if request.method == "POST":
        new_status = request.form.get("status", status)
        note = request.form.get("note", "").strip()
        db.save_review(device_id, item_index, new_status, note if note else None)
        return redirect(
            url_for("device_item_detail", device_id=device_id, item_index=item_index)
        )

    return render_template(
        "item.html",
        device=device,
        item=item,
        index=item_index,
    )


@app.route("/device/<int:device_id>/dashboard")
@requires_auth(auth_manager)
def device_dashboard(device_id: int):
    """Display device dashboard with summary."""
    device = db.get_device(device_id)
    if device is None:
        abort(404)

    reviews = db.get_reviews_for_device(device_id)
    summary = compute_device_summary(checklist_items, reviews)

    return render_template(
        "dashboard.html",
        device=device,
        summary=summary,
    )


@app.route("/device/<int:device_id>/export/csv")
@requires_auth(auth_manager)
def device_export_csv(device_id: int):
    """Export device checklist to CSV."""
    device = db.get_device(device_id)
    if device is None:
        abort(404)

    reviews = db.get_reviews_for_device(device_id)
    items = build_device_items(checklist_items, reviews)

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)

    writer.writerow([
        "Device Name",
        "Hostname",
        "Control ID",
        "Section",
        "Title",
        "Status",
        "Comment",
        "Rationale",
        "Fix Text",
    ])

    for item in items:
        writer.writerow([
            device["name"],
            device.get("hostname", "") or "",
            item.get("control_id", ""),
            item.get("section", ""),
            item.get("title", ""),
            item.get("status", ""),
            item.get("comment", ""),
            item.get("rationale", ""),
            item.get("fix_text", ""),
        ])

    csv_data = output.getvalue()
    output.close()

    safe_name = sanitize_filename(device["name"])
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"pfsense_benchmark_{safe_name}_{timestamp}.csv"

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        },
    )


@app.route("/device/<int:device_id>/report")
@requires_auth(auth_manager)
def device_report(device_id: int):
    """Generate compliance report for device."""
    device = db.get_device(device_id)
    if device is None:
        abort(404)

    reviews = db.get_reviews_for_device(device_id)
    summary = compute_device_summary(checklist_items, reviews)
    items = build_device_items(checklist_items, reviews)

    non_compliant = [i for i in items if i.get("status") == ComplianceStatus.NON_COMPLIANT.value]
    not_reviewed = [i for i in items if i.get("status") == ComplianceStatus.NOT_REVIEWED.value]

    generated_on = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return render_template(
        "report.html",
        device=device,
        summary=summary,
        non_compliant=non_compliant,
        not_reviewed=not_reviewed,
        generated_on=generated_on,
    )


@app.route("/device/<int:device_id>/autocheck")
@requires_auth(auth_manager)
def device_autocheck(device_id: int):
    """Run automated checks for a device."""
    device = db.get_device(device_id)
    if device is None:
        abort(404)

    run_auto_checks_ssh(device_id, device)
    return redirect(url_for("device_checklist", device_id=device_id))


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------

if __name__ == "__main__":
    if Config.DEBUG:
        logger.warning("Running in DEBUG mode - DO NOT use in production!")

    app.run(
        debug=Config.DEBUG,
        host="127.0.0.1",
        port=5000
    )
