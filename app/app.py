from flask import (
    Flask,
    render_template,
    abort,
    request,
    redirect,
    url_for,
    Response,
)
import json
import os
import sqlite3
import csv
import io
from datetime import datetime
import paramiko
import xml.etree.ElementTree as ET
import re

app = Flask(__name__)

# -------------------------------------------------------------------
# Paths / data load
# -------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, "..", "pfsense_benchmark.json")
CKL_PATH = os.path.join(BASE_DIR, "..", "pfsense_benchmark.ckl")
DB_PATH = os.path.join(BASE_DIR, "..", "reviews.db")

STATUS_MAP = {
    "NotAFinding": "Compliant",
    "Open": "Non Compliant",
    "Not_Applicable": "Non Applicable",
    "Not_Reviewed": "Not Reviewed",
}


def load_ckl_items(path: str):
    """
    Load checklist items from a DISA-style CKL file.
    Converts STIG fields to the structure the app expects.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    root = ET.parse(path).getroot()
    istig = root.find(".//STIGS/iSTIG")
    if istig is None:
        raise ValueError("No <iSTIG> block found in CKL.")

    items = []
    for idx, vuln in enumerate(istig.findall("VULN")):
        stig_data = {}
        for sd in vuln.findall("STIG_DATA"):
            key = (sd.findtext("VULN_ATTRIBUTE") or "").strip()
            val = (sd.findtext("ATTRIBUTE_DATA") or "").strip()
            if key:
                stig_data[key] = val

        raw_control = stig_data.get("Rule_ID") or stig_data.get("Vuln_Num") or ""
        control_id = raw_control[3:] if raw_control.upper().startswith("PF-") else raw_control
        control_id = control_id.strip() or f"item-{idx+1}"

        group_title = stig_data.get("Group_Title", "").strip()
        section = group_title.split(" - ")[0].strip() if " - " in group_title else group_title
        section = section or "Unknown"

        status_raw = (vuln.findtext("STATUS") or "Not_Reviewed").strip()
        status = STATUS_MAP.get(status_raw, "Not Reviewed")

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

    return items


def load_checklist_items():
    """
    Prefer the CKL if present; fall back to the legacy JSON for safety.
    """
    if os.path.exists(CKL_PATH):
        try:
            return load_ckl_items(CKL_PATH)
        except Exception as exc:  # pragma: no cover - startup diagnostics
            print(f"[WARN] Failed loading CKL ({CKL_PATH}): {exc}. Falling back to JSON.")

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


checklist_items = load_checklist_items()

# Map control_id -> index for fast lookup
CONTROL_ID_TO_INDEX = {}
for idx, item in enumerate(checklist_items):
    cid = item.get("control_id")
    if cid:
        CONTROL_ID_TO_INDEX[cid.strip()] = idx


# -------------------------------------------------------------------
# DB helpers
# -------------------------------------------------------------------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def extend_devices_schema(conn):
    """Add new columns to devices table if they are missing."""
    cur = conn.execute("PRAGMA table_info(devices);")
    cols = [row[1] for row in cur.fetchall()]

    def add_col(name, col_type="TEXT"):
        if name not in cols:
            conn.execute(f"ALTER TABLE devices ADD COLUMN {name} {col_type};")

    add_col("mgmt_ip", "TEXT")
    add_col("ssh_user", "TEXT")
    add_col("ssh_password", "TEXT")
    conn.commit()


def init_db():
    conn = get_db()

    # Devices
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS devices (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT NOT NULL,
            hostname TEXT,
            notes    TEXT
        );
        """
    )
    conn.commit()

    extend_devices_schema(conn)

    # Scrub any previously stored SSH passwords to avoid keeping secrets locally.
    try:
        conn.execute("UPDATE devices SET ssh_password = NULL WHERE ssh_password IS NOT NULL;")
        conn.commit()
    except Exception:
        pass

    # Per-device reviews
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reviews (
            device_id  INTEGER NOT NULL,
            item_index INTEGER NOT NULL,
            status     TEXT NOT NULL,
            note       TEXT,
            PRIMARY KEY (device_id, item_index),
            FOREIGN KEY (device_id) REFERENCES devices(id)
        );
        """
    )

    conn.commit()
    conn.close()


def get_device(device_id: int):
    conn = get_db()
    cur = conn.execute("SELECT * FROM devices WHERE id = ?;", (device_id,))
    row = cur.fetchone()
    conn.close()
    if row is None:
        return None
    return dict(row)


def get_all_devices():
    conn = get_db()
    cur = conn.execute("SELECT * FROM devices ORDER BY id;")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_device(name: str, hostname: str, notes: str,
                  mgmt_ip: str, ssh_user: str):
    conn = get_db()
    cur = conn.execute(
        """
        INSERT INTO devices (name, hostname, notes, mgmt_ip, ssh_user, ssh_password)
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        (name, hostname or None, notes or None,
         mgmt_ip or None, ssh_user or None, None),
    )
    conn.commit()
    device_id = cur.lastrowid
    conn.close()
    return device_id


def update_device(device_id: int, name: str, hostname: str, notes: str,
                  mgmt_ip: str, ssh_user: str):
    conn = get_db()
    conn.execute(
        """
        UPDATE devices
        SET name = ?, hostname = ?, notes = ?, mgmt_ip = ?, ssh_user = ?, ssh_password = NULL
        WHERE id = ?;
        """,
        (name, hostname or None, notes or None,
         mgmt_ip or None, ssh_user or None, device_id),
    )
    conn.commit()
    conn.close()


def delete_device_and_reviews(device_id: int):
    conn = get_db()
    conn.execute("DELETE FROM reviews WHERE device_id = ?;", (device_id,))
    conn.execute("DELETE FROM devices WHERE id = ?;", (device_id,))
    conn.commit()
    conn.close()


def get_reviews_for_device(device_id: int):
    """Return dict: item_index -> {status, note}."""
    conn = get_db()
    cur = conn.execute(
        "SELECT item_index, status, note FROM reviews WHERE device_id = ?;",
        (device_id,),
    )
    rows = cur.fetchall()
    conn.close()
    out = {}
    for r in rows:
        out[r["item_index"]] = {"status": r["status"], "note": r["note"]}
    return out


def save_review(device_id: int, item_index: int, status: str, note: str | None):
    conn = get_db()
    conn.execute(
        """
        INSERT INTO reviews (device_id, item_index, status, note)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(device_id, item_index) DO UPDATE SET
            status = excluded.status,
            note   = excluded.note;
        """,
        (device_id, item_index, status, note),
    )
    conn.commit()
    conn.close()


def compute_device_summary(device_id: int):
    reviews = get_reviews_for_device(device_id)

    total_items = len(checklist_items)
    status_counts = {
        "Not Reviewed": 0,
        "Compliant": 0,
        "Non Compliant": 0,
        "Non Applicable": 0,
    }
    section_non_compliant = {}

    for idx, base_item in enumerate(checklist_items):
        section = base_item.get("section", "Unknown")
        status = base_item.get("status", "Not Reviewed")

        if idx in reviews:
            status = reviews[idx]["status"]

        if status not in status_counts:
            status = "Not Reviewed"

        status_counts[status] += 1

        if status == "Non Compliant":
            section_non_compliant[section] = section_non_compliant.get(section, 0) + 1

    reviewed = total_items - status_counts["Not Reviewed"]
    not_reviewed = status_counts["Not Reviewed"]
    compliant = status_counts["Compliant"]
    non_compliant = status_counts["Non Compliant"]
    non_applicable = status_counts["Non Applicable"]

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


def build_device_items(device_id: int):
    """
    Build list of items for a given device.

    IMPORTANT: we ignore the benchmark's default comments and only show
    per-device review notes.
    """
    reviews = get_reviews_for_device(device_id)
    items_for_view = []

    for idx, base_item in enumerate(checklist_items):
        item = dict(base_item)
        item["index"] = idx

        status = item.get("status", "Not Reviewed")
        comment = ""  # per-device comments only

        if idx in reviews:
            status = reviews[idx]["status"]
            if reviews[idx]["note"]:
                comment = reviews[idx]["note"]

        item["status"] = status
        item["comment"] = comment
        items_for_view.append(item)

    return items_for_view


# -------------------------------------------------------------------
# Auto-check logic (SSH + config.xml)
# -------------------------------------------------------------------

def _mark_control(device_id: int, control_id: str,
                  status: str, note: str):
    idx = CONTROL_ID_TO_INDEX.get(control_id)
    if idx is None:
        return
    save_review(device_id, idx, status, note)


def _run_config_checks(
    device_id: int,
    device: dict,
    root: ET.Element,
    ssh_client: paramiko.SSHClient | None = None,
):
    """
    Run CIS-style checks against config.xml (and, if available, SSH-visible files).
    """

    # ---------- 1.1 Ensure SSH warning banner is configured ----------
    if ssh_client is not None:
        try:
            stdin, stdout, stderr = ssh_client.exec_command(
                "grep -E '^Banner\\s+' /etc/ssh/sshd_config || echo ''"
            )
            banner_line = stdout.read().decode("utf-8", errors="ignore").strip()

            if "Banner" in banner_line:
                stdin, stdout, stderr = ssh_client.exec_command(
                    "test -s /etc/issue.net && echo HAS_BANNER || echo NO_BANNER"
                )
                issue_flag = stdout.read().decode("utf-8", errors="ignore").strip()
                if issue_flag == "HAS_BANNER":
                    _mark_control(
                        device_id,
                        "1.1",
                        "Compliant",
                        "Banner directive present in sshd_config and /etc/issue.net is non-empty.",
                    )
                else:
                    _mark_control(
                        device_id,
                        "1.1",
                        "Non Compliant",
                        "Banner directive present, but /etc/issue.net is missing or empty.",
                    )
            else:
                _mark_control(
                    device_id,
                    "1.1",
                    "Non Compliant",
                    "No Banner directive found in /etc/ssh/sshd_config.",
                )
        except Exception as e:
            _mark_control(
                device_id,
                "1.1",
                "Not Reviewed",
                f"Auto-check error while reading sshd_config: {type(e).__name__} - {e}",
            )

    # ---------- 1.3 Ensure MOTD is set ----------
    if ssh_client is not None:
        try:
            stdin, stdout, stderr = ssh_client.exec_command(
                "test -s /etc/motd && echo HAS_MOTD || echo NO_MOTD"
            )
            flag = stdout.read().decode("utf-8", errors="ignore").strip()
            if flag == "HAS_MOTD":
                _mark_control(
                    device_id,
                    "1.3",
                    "Compliant",
                    "/etc/motd exists and is non-empty.",
                )
            else:
                _mark_control(
                    device_id,
                    "1.3",
                    "Non Compliant",
                    "/etc/motd is missing or empty.",
                )
        except Exception as e:
            _mark_control(
                device_id,
                "1.3",
                "Not Reviewed",
                f"Auto-check error while reading /etc/motd: {type(e).__name__} - {e}",
            )

    # ---------- 1.4 Ensure Hostname is set ----------
    hostname = root.findtext(".//system/hostname")
    if hostname:
        _mark_control(
            device_id,
            "1.4",
            "Compliant",
            f"Hostname set to '{hostname}'.",
        )
    else:
        _mark_control(
            device_id,
            "1.4",
            "Non Compliant",
            "Hostname is not set in config.xml.",
        )

    # ---------- 1.5 Ensure DNS server is configured ----------
    dns_servers = root.findall(".//system/dnsserver")
    if dns_servers:
        dns_list = [d.text for d in dns_servers if d.text]
        if dns_list:
            _mark_control(
                device_id,
                "1.5",
                "Compliant",
                f"DNS servers configured: {', '.join(dns_list)}",
            )
        else:
            _mark_control(
                device_id,
                "1.5",
                "Non Compliant",
                "system/dnsserver entries present but empty.",
            )
    else:
        _mark_control(
            device_id,
            "1.5",
            "Non Compliant",
            "No DNS servers defined in system/dnsserver.",
        )

    # ---------- 1.6 Ensure IPv6 is disabled if not used (basic WAN check) ----------
    ipproto = root.findtext(".//interfaces/wan/ipprotocol")
    if ipproto:
        ipproto_lower = ipproto.lower()
        if ipproto_lower in ("inet", "ipv4"):
            _mark_control(
                device_id,
                "1.6",
                "Compliant",
                f"WAN ipprotocol is '{ipproto}', IPv4-only.",
            )
        else:
            _mark_control(
                device_id,
                "1.6",
                "Non Compliant",
                f"WAN ipprotocol is '{ipproto}' (IPv6 or dual-stack enabled). Verify IPv6 usage vs CIS requirements.",
            )
    else:
        _mark_control(
            device_id,
            "1.6",
            "Not Reviewed",
            "No ipprotocol value found for WAN in config.xml.",
        )

    # ---------- 1.8 Ensure Web Management is set to HTTPS ----------
    protocol = root.findtext(".//system/webgui/protocol")
    if protocol and protocol.lower() == "https":
        _mark_control(
            device_id,
            "1.8",
            "Compliant",
            "WebGUI protocol is HTTPS.",
        )
    else:
        _mark_control(
            device_id,
            "1.8",
            "Non Compliant",
            f"WebGUI protocol is '{protocol or 'not set'}' (expected HTTPS).",
        )

    # ---------- 1.10 Ensure NTP is configured and enabled ----------
    timeservers = (root.findtext(".//system/timeservers") or "").strip()
    ntpd_enable = (root.findtext(".//ntpd/enable") or "").strip().lower()

    if timeservers:
        if ntpd_enable == "enabled":
            _mark_control(
                device_id,
                "1.10",
                "Compliant",
                f"NTP enabled with time servers: {timeservers}",
            )
        else:
            _mark_control(
                device_id,
                "1.10",
                "Non Compliant",
                f"NTP time servers configured ({timeservers}) but ntpd is not enabled in config.xml.",
            )
    else:
        _mark_control(
            device_id,
            "1.10",
            "Non Compliant",
            "No NTP time servers defined under system/timeservers.",
        )

    # ---------- 2.1 Ensure Sessions Timeout <= 10 minutes ----------
    session_timeout_txt = root.findtext(".//system/webgui/session_timeout")
    if session_timeout_txt is not None:
        try:
            val = int(session_timeout_txt)
            if val <= 10:
                _mark_control(
                    device_id,
                    "2.1",
                    "Compliant",
                    f"Session timeout set to {val} minutes.",
                )
            else:
                _mark_control(
                    device_id,
                    "2.1",
                    "Non Compliant",
                    f"Session timeout set to {val} minutes (> 10).",
                )
        except ValueError:
            _mark_control(
                device_id,
                "2.1",
                "Non Compliant",
                f"session_timeout value '{session_timeout_txt}' is not a valid integer.",
            )
    else:
        _mark_control(
            device_id,
            "2.1",
            "Non Compliant",
            "No webgui/session_timeout value set in config.xml.",
        )

    # ---------- 2.2 Ensure LDAP/RADIUS auth server configured ----------
    authservers = root.findall(".//authserver")
    if authservers:
        names = []
        for a in authservers:
            name = a.findtext("name") or a.findtext("description")
            if name:
                names.append(name)
        if names:
            _mark_control(
                device_id,
                "2.2",
                "Compliant",
                "Authentication servers configured: " + ", ".join(names),
            )
        else:
            _mark_control(
                device_id,
                "2.2",
                "Compliant",
                "Authentication servers configured (names not found in XML).",
            )
    else:
        _mark_control(
            device_id,
            "2.2",
            "Non Compliant",
            "No LDAP/RADIUS auth servers (<authserver> blocks) found in config.xml.",
        )

    # ---------- 3.1 / 3.2 SNMP disabled / Captive Portal disabled ----------
    snmp_rocommunity = (root.findtext(".//snmpd/rocommunity") or "").strip()
    snmp_pollport = (root.findtext(".//snmpd/pollport") or "").strip()

    if not snmp_rocommunity:
        _mark_control(
            device_id,
            "3.1",
            "Compliant",
            "SNMP read-only community is empty; SNMP appears to be disabled.",
        )
    else:
        _mark_control(
            device_id,
            "3.1",
            "Non Compliant",
            f"SNMP rocommunity is configured (pollport {snmp_pollport}). Verify this meets CIS hardening requirements.",
        )

    captiveportal = root.find(".//captiveportal")
    has_captive_children = len(captiveportal) > 0 if captiveportal is not None else False

    if has_captive_children:
        _mark_control(
            device_id,
            "3.2",
            "Non Compliant",
            "Captive portal appears to have configuration present. Verify if this is required and hardened.",
        )
    else:
        _mark_control(
            device_id,
            "3.2",
            "Compliant",
            "No captive portal configuration detected in <captiveportal>.",
        )

    # ---------- 6.1 Ensure syslog is configured ----------
    remoteserver = (root.findtext(".//syslog/remoteserver") or "").strip()
    syslog_enable = (root.findtext(".//syslog/enable") or "").strip().lower()

    if remoteserver:
        _mark_control(
            device_id,
            "6.1",
            "Compliant",
            f"Remote syslog server configured: {remoteserver}",
        )
    else:
        _mark_control(
            device_id,
            "6.1",
            "Non Compliant",
            "No remote syslog server configured under <syslog><remoteserver>.",
        )

    # ---------- 5.1.x SNMP trap / NET-SNMP ----------
    installed_pkgs = root.find("installedpackages")
    installed_pkgs_text = (
        ET.tostring(installed_pkgs, encoding="unicode").lower()
        if installed_pkgs is not None else ""
    )

    snmpd_conf_text = ""
    if ssh_client is not None:
        try:
            stdin, stdout, stderr = ssh_client.exec_command(
                "for p in /var/net-snmp/snmpd.conf /var/etc/snmpd.conf /etc/snmpd.conf; "
                "do [ -f \"$p\" ] && cat \"$p\"; done"
            )
            snmpd_conf_text = stdout.read().decode("utf-8", errors="ignore")
        except Exception:
            snmpd_conf_text = ""

    has_snmp = bool(snmp_rocommunity.strip()) or bool(snmpd_conf_text.strip())

    # Detect trap configuration from either XML or snmpd.conf
    trapserver = (root.findtext(".//snmpd/trapserver") or "").strip()
    trapstring = (root.findtext(".//snmpd/trapstring") or "").strip()

    trap_conf_found = False
    if trapserver or trapstring:
        trap_conf_found = True
    if snmpd_conf_text:
        # Look for common trap directives in net-snmp config
        if re.search(r"trap[s2]?sink\\s+\\S+", snmpd_conf_text, re.IGNORECASE) or \
           re.search(r"trapsess\\s+.*\\s+\\S+", snmpd_conf_text, re.IGNORECASE):
            trap_conf_found = True

    if not has_snmp:
        for cid in ("5.1.1", "5.1.2", "5.1.3"):
            _mark_control(
                device_id,
                cid,
                "Non Applicable",
                "SNMP appears disabled (no rocommunity and no snmpd.conf content).",
            )
    else:
        if trap_conf_found:
            _mark_control(
                device_id,
                "5.1.1",
                "Compliant",
                "SNMP trap receiver configuration detected.",
            )
            _mark_control(
                device_id,
                "5.1.2",
                "Compliant",
                "SNMP traps appear enabled (trap settings present).",
            )
        else:
            _mark_control(
                device_id,
                "5.1.1",
                "Non Compliant",
                "No SNMP trap receiver found in config.xml or snmpd.conf.",
            )
            _mark_control(
                device_id,
                "5.1.2",
                "Non Compliant",
                "No SNMP trap configuration found; verify traps are enabled as required.",
            )

        if "net-snmp" in installed_pkgs_text or snmpd_conf_text:
            _mark_control(
                device_id,
                "5.1.3",
                "Compliant",
                "NET-SNMP detected (package entry or snmpd.conf present).",
            )
        else:
            _mark_control(
                device_id,
                "5.1.3",
                "Non Compliant",
                "SNMP is enabled but NET-SNMP evidence not found in installed packages or config.",
            )

    # ---------- 5.2.1 Timezone ----------
    timezone = (root.findtext(".//system/timezone") or "").strip()
    if timezone:
        _mark_control(
            device_id,
            "5.2.1",
            "Compliant",
            f"System time zone set to '{timezone}'.",
        )
    else:
        _mark_control(
            device_id,
            "5.2.1",
            "Non Compliant",
            "System time zone is not set under <system><timezone>.",
        )

    # ---------- 5.3.1 DNSSEC ----------
    unbound = root.find("unbound")
    if unbound is not None:
        dnssec = unbound.find("dnssec")
        if dnssec is not None:
            _mark_control(
                device_id,
                "5.3.1",
                "Compliant",
                "Unbound DNS resolver has DNSSEC enabled (<dnssec /> present).",
            )
        else:
            _mark_control(
                device_id,
                "5.3.1",
                "Non Compliant",
                "Unbound DNS resolver does not have <dnssec /> configured.",
            )
    else:
        _mark_control(
            device_id,
            "5.3.1",
            "Not Reviewed",
            "No <unbound> DNS resolver block found; verify DNSSEC configuration manually.",
        )

    # ---------- 5.4.x / 5.5.1 VPN checks (mostly applicability) ----------
    has_openvpn_server = root.find(".//openvpn/openvpn-server") is not None
    has_ipsec_phase1 = root.find(".//ipsec/phase1") is not None

    if not (has_openvpn_server or has_ipsec_phase1):
        _mark_control(
            device_id,
            "5.4.1",
            "Non Applicable",
            "No OpenVPN server or IPsec Phase1 configuration detected.",
        )
    else:
        _mark_control(
            device_id,
            "5.4.1",
            "Not Reviewed",
            "VPN configuration detected; verify VPN authentication uses RADIUS or LDAP.",
        )

    if not (has_openvpn_server or has_ipsec_phase1):
        _mark_control(
            device_id,
            "5.4.2",
            "Non Applicable",
            "No VPN portal (OpenVPN/IPsec) configuration detected.",
        )
    else:
        _mark_control(
            device_id,
            "5.4.2",
            "Not Reviewed",
            "VPN configuration detected; verify a trusted signed certificate is used for the VPN portal.",
        )

    if not has_openvpn_server:
        _mark_control(
            device_id,
            "5.4.3",
            "Non Applicable",
            "No OpenVPN server configuration detected.",
        )
    else:
        _mark_control(
            device_id,
            "5.4.3",
            "Not Reviewed",
            "OpenVPN server found; verify TLS encryption settings per CIS benchmark.",
        )

    if not has_openvpn_server:
        _mark_control(
            device_id,
            "5.5.1",
            "Non Applicable",
            "No OpenVPN server configuration detected.",
        )
    else:
        _mark_control(
            device_id,
            "5.5.1",
            "Not Reviewed",
            "OpenVPN server found; verify cipher and hash algorithms per CIS benchmark.",
        )

    # ---------- 4.x Firewall policy / WAN rule analysis ----------
    filter_elem = root.find(".//filter")
    if filter_elem is not None:
        wan_rules = []
        for r in filter_elem.findall("rule"):
            iface = (r.findtext("interface") or "").strip()
            if iface == "wan":
                wan_rules.append(r)

        # 4.1.1 Any destination
        any_dest_rules = []
        for r in wan_rules:
            dest = r.find("destination")
            if dest is not None:
                addr = dest.findtext("network") or dest.findtext("address") or ""
                if addr.strip().lower() == "any":
                    any_dest_rules.append(r)

        if any_dest_rules:
            _mark_control(
                device_id,
                "4.1.1",
                "Non Compliant",
                f"{len(any_dest_rules)} WAN rule(s) allow ANY destination.",
            )
        else:
            _mark_control(
                device_id,
                "4.1.1",
                "Compliant",
                "No WAN rules allow ANY destination.",
            )

        # 4.1.2 Any source
        any_src_rules = []
        for r in wan_rules:
            src = r.find("source")
            if src is not None:
                addr = src.findtext("network") or src.findtext("address") or ""
                if addr.strip().lower() == "any":
                    any_src_rules.append(r)

        if any_src_rules:
            _mark_control(
                device_id,
                "4.1.2",
                "Non Compliant",
                f"{len(any_src_rules)} WAN rule(s) allow ANY source.",
            )
        else:
            _mark_control(
                device_id,
                "4.1.2",
                "Compliant",
                "No WAN rules allow ANY source.",
            )

        # 4.1.3 Any service/protocol
        any_service_rules = []
        for r in wan_rules:
            proto = (r.findtext("protocol") or "").strip().lower()
            if proto in ("any", "all", ""):
                any_service_rules.append(r)

        if any_service_rules:
            _mark_control(
                device_id,
                "4.1.3",
                "Non Compliant",
                f"{len(any_service_rules)} WAN rule(s) permit ANY service/protocol.",
            )
        else:
            _mark_control(
                device_id,
                "4.1.3",
                "Compliant",
                "No WAN rules allow ANY service/protocol.",
            )

        # 4.1.4 Unused / disabled
        disabled_rules = [r for r in wan_rules if r.find("disabled") is not None]
        if disabled_rules:
            _mark_control(
                device_id,
                "4.1.4",
                "Non Compliant",
                f"{len(disabled_rules)} WAN rule(s) are disabled/unused.",
            )
        else:
            _mark_control(
                device_id,
                "4.1.4",
                "Compliant",
                "No disabled/unused WAN rules found.",
            )

        # 4.1.5 Logging on all WAN rules
        no_log_rules = [r for r in wan_rules if r.find("log") is None]
        if no_log_rules:
            _mark_control(
                device_id,
                "4.1.5",
                "Non Compliant",
                f"{len(no_log_rules)} WAN rule(s) do NOT have logging enabled.",
            )
        else:
            _mark_control(
                device_id,
                "4.1.5",
                "Compliant",
                "All WAN rules have logging enabled.",
            )

        # 4.1.6 ICMP rules
        bad_icmp_rules = []
        for r in wan_rules:
            proto = (r.findtext("protocol") or "").strip().lower()
            if proto == "icmp":
                icmp_type = (r.findtext("icmptype") or "").strip().lower()
                if icmp_type in ("", "any", None):
                    bad_icmp_rules.append(r)

        if bad_icmp_rules:
            _mark_control(
                device_id,
                "4.1.6",
                "Non Compliant",
                f"{len(bad_icmp_rules)} insecure ICMP rule(s) on WAN.",
            )
        else:
            _mark_control(
                device_id,
                "4.1.6",
                "Compliant",
                "All WAN ICMP rules have specific ICMP types (or none exist).",
            )
    else:
        for cid in ("4.1.1", "4.1.2", "4.1.3", "4.1.4", "4.1.5", "4.1.6"):
            _mark_control(
                device_id,
                cid,
                "Not Reviewed",
                "No <filter> block found in config.xml; cannot evaluate WAN rules.",
            )


def run_auto_checks_ssh(device_id: int, device: dict):
    """SSH into the device, pull /conf/config.xml, run checks."""
    mgmt_ip = (device.get("mgmt_ip") or "").strip()
    ssh_user = (device.get("ssh_user") or "").strip()

    if not mgmt_ip or not ssh_user:
        return

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            mgmt_ip,
            username=ssh_user,
            timeout=10,
            look_for_keys=True,
            allow_agent=True,
        )

        stdin, stdout, stderr = client.exec_command("cat /conf/config.xml")
        xml_data = stdout.read().decode("utf-8", errors="ignore")
        err = stderr.read().decode("utf-8", errors="ignore")

        if not xml_data:
            note = f"Auto-check failed: empty config.xml output. stderr: {err}"
            _mark_control(device_id, "1.4", "Not Reviewed", note)
            return

        root = ET.fromstring(xml_data)
        _run_config_checks(device_id, device, root, ssh_client=client)

    except Exception as e:
        note = f"Auto-check SSH error: {type(e).__name__} - {e}"
        print(f"[AUTO-CHECK][device {device_id}] {note}")
        _mark_control(device_id, "1.4", "Not Reviewed", note)

    finally:
        try:
            client.close()
        except Exception:
            pass


# -------------------------------------------------------------------
# Init DB
# -------------------------------------------------------------------

init_db()


# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------

@app.route("/")
def index():
    return redirect(url_for("devices"))


@app.route("/devices")
def devices():
    devices_list = get_all_devices()
    return render_template("devices.html", devices=devices_list)


@app.route("/devices/new", methods=["GET", "POST"])
def new_device():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        hostname = request.form.get("hostname", "").strip()
        notes = request.form.get("notes", "").strip()
        mgmt_ip = request.form.get("mgmt_ip", "").strip()
        ssh_user = request.form.get("ssh_user", "").strip()

        if not name:
            return "Device name is required.", 400

        device_id = create_device(name, hostname, notes,
                                  mgmt_ip, ssh_user)
        return redirect(url_for("device_checklist", device_id=device_id))

    return render_template("device_form.html")


@app.route("/devices/<int:device_id>/edit", methods=["GET", "POST"])
def edit_device(device_id: int):
    device = get_device(device_id)
    if device is None:
        abort(404)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        hostname = request.form.get("hostname", "").strip()
        notes = request.form.get("notes", "").strip()
        mgmt_ip = request.form.get("mgmt_ip", "").strip()
        ssh_user = request.form.get("ssh_user", "").strip()

        if not name:
            return "Device name is required.", 400

        update_device(device_id, name, hostname, notes,
                      mgmt_ip, ssh_user)
        return redirect(url_for("devices"))

    return render_template("device_edit.html", device=device)


@app.route("/devices/<int:device_id>/delete", methods=["POST"])
def delete_device_route(device_id: int):
    device = get_device(device_id)
    if device is None:
        abort(404)

    delete_device_and_reviews(device_id)
    return redirect(url_for("devices"))


@app.route("/device/<int:device_id>/checklist")
def device_checklist(device_id: int):
    device = get_device(device_id)
    if device is None:
        abort(404)

    items_for_view = build_device_items(device_id)
    summary = compute_device_summary(device_id)

    return render_template(
        "checklist.html",
        device=device,
        items=items_for_view,
        summary=summary,
    )


@app.route("/device/<int:device_id>/item/<int:item_index>", methods=["GET", "POST"])
def device_item_detail(device_id: int, item_index: int):
    device = get_device(device_id)
    if device is None:
        abort(404)

    if item_index < 0 or item_index >= len(checklist_items):
        abort(404)

    base_item = dict(checklist_items[item_index])

    reviews = get_reviews_for_device(device_id)
    status = base_item.get("status", "Not Reviewed")
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
        save_review(device_id, item_index, new_status, note if note else None)
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
def device_dashboard(device_id: int):
    device = get_device(device_id)
    if device is None:
        abort(404)

    summary = compute_device_summary(device_id)
    return render_template(
        "dashboard.html",
        device=device,
        summary=summary,
    )


@app.route("/device/<int:device_id>/export/csv")
def device_export_csv(device_id: int):
    device = get_device(device_id)
    if device is None:
        abort(404)

    items = build_device_items(device_id)

    output = io.StringIO()
    writer = csv.writer(output)

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

    safe_name = str(device["name"]).replace(" ", "_")
    filename = f"pfsense_benchmark_{safe_name}.csv"

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        },
    )


@app.route("/device/<int:device_id>/report")
def device_report(device_id: int):
    device = get_device(device_id)
    if device is None:
        abort(404)

    summary = compute_device_summary(device_id)
    items = build_device_items(device_id)
    non_compliant = [i for i in items if i.get("status") == "Non Compliant"]
    not_reviewed = [i for i in items if i.get("status") == "Not Reviewed"]

    generated_on = datetime.now().strftime("%Y-%m-%d %H:%M")

    return render_template(
        "report.html",
        device=device,
        summary=summary,
        non_compliant=non_compliant,
        not_reviewed=not_reviewed,
        generated_on=generated_on,
    )


@app.route("/device/<int:device_id>/autocheck")
def device_autocheck(device_id: int):
    device = get_device(device_id)
    if device is None:
        abort(404)

    run_auto_checks_ssh(device_id, device)
    return redirect(url_for("device_checklist", device_id=device_id))


if __name__ == "__main__":
    app.run(debug=True)
