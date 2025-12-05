"""
Data-driven automated checks for pfSense CIS/STIG compliance.
"""

import logging
import re
from typing import Optional, Tuple, Callable
from defusedxml import ElementTree as ET

from .ssh_client import SecureSSHClient

logger = logging.getLogger(__name__)


CheckResult = Tuple[str, str]  # (status, note)


class AutoChecker:
    """Automated compliance checker for pfSense."""

    def __init__(self, config_root: ET.Element, ssh_client: Optional[SecureSSHClient] = None):
        """
        Initialize auto-checker.

        Args:
            config_root: Parsed pfSense config.xml root element
            ssh_client: Optional SSH client for filesystem checks
        """
        self.config = config_root
        self.ssh = ssh_client

    def check_ssh_banner(self) -> CheckResult:
        """1.1: Ensure SSH warning banner is configured."""
        if not self.ssh:
            return ("Not Reviewed", "SSH connection required for this check.")

        try:
            # Read sshd_config using SFTP
            sshd_config = self.ssh.read_file("/etc/ssh/sshd_config")
            if not sshd_config:
                return ("Non Compliant", "Cannot read /etc/ssh/sshd_config.")

            if not re.search(r"^Banner\s+", sshd_config, re.MULTILINE):
                return ("Non Compliant", "No Banner directive found in /etc/ssh/sshd_config.")

            # Check if banner file exists and has content
            if self.ssh.file_exists("/etc/issue.net"):
                issue_content = self.ssh.read_file("/etc/issue.net")
                if issue_content and issue_content.strip():
                    return ("Compliant", "Banner directive present and /etc/issue.net has content.")
                else:
                    return ("Non Compliant", "Banner directive present but /etc/issue.net is empty.")
            else:
                return ("Non Compliant", "Banner directive present but /etc/issue.net is missing.")

        except Exception as e:
            return ("Not Reviewed", f"Auto-check error: {type(e).__name__} - {e}")

    def check_motd(self) -> CheckResult:
        """1.3: Ensure MOTD is set."""
        if not self.ssh:
            return ("Not Reviewed", "SSH connection required for this check.")

        try:
            if self.ssh.file_exists("/etc/motd"):
                motd_content = self.ssh.read_file("/etc/motd")
                if motd_content and motd_content.strip():
                    return ("Compliant", "/etc/motd exists and has content.")
                else:
                    return ("Non Compliant", "/etc/motd is empty.")
            else:
                return ("Non Compliant", "/etc/motd is missing.")

        except Exception as e:
            return ("Not Reviewed", f"Auto-check error: {type(e).__name__} - {e}")

    def check_hostname(self) -> CheckResult:
        """1.4: Ensure Hostname is set."""
        hostname = self.config.findtext(".//system/hostname")
        if hostname and hostname.strip():
            return ("Compliant", f"Hostname set to '{hostname}'.")
        return ("Non Compliant", "Hostname is not set in config.xml.")

    def check_dns_servers(self) -> CheckResult:
        """1.5: Ensure DNS server is configured."""
        dns_servers = self.config.findall(".//system/dnsserver")
        if dns_servers:
            dns_list = [d.text for d in dns_servers if d.text]
            if dns_list:
                return ("Compliant", f"DNS servers configured: {', '.join(dns_list)}")
            return ("Non Compliant", "system/dnsserver entries present but empty.")
        return ("Non Compliant", "No DNS servers defined in system/dnsserver.")

    def check_ipv6_disabled(self) -> CheckResult:
        """1.6: Ensure IPv6 is disabled if not used."""
        ipproto = self.config.findtext(".//interfaces/wan/ipprotocol")
        if ipproto:
            ipproto_lower = ipproto.lower()
            if ipproto_lower in ("inet", "ipv4"):
                return ("Compliant", f"WAN ipprotocol is '{ipproto}', IPv4-only.")
            return (
                "Non Compliant",
                f"WAN ipprotocol is '{ipproto}' (IPv6 or dual-stack enabled). "
                "Verify IPv6 usage vs CIS requirements."
            )
        return ("Not Reviewed", "No ipprotocol value found for WAN in config.xml.")

    def check_webgui_https(self) -> CheckResult:
        """1.8: Ensure Web Management is set to HTTPS."""
        protocol = self.config.findtext(".//system/webgui/protocol")
        if protocol and protocol.lower() == "https":
            return ("Compliant", "WebGUI protocol is HTTPS.")
        return ("Non Compliant", f"WebGUI protocol is '{protocol or 'not set'}' (expected HTTPS).")

    def check_ntp_configured(self) -> CheckResult:
        """1.10: Ensure NTP is configured and enabled."""
        timeservers = (self.config.findtext(".//system/timeservers") or "").strip()
        ntpd_enable = (self.config.findtext(".//ntpd/enable") or "").strip().lower()

        if timeservers:
            if ntpd_enable == "enabled":
                return ("Compliant", f"NTP enabled with time servers: {timeservers}")
            return (
                "Non Compliant",
                f"NTP time servers configured ({timeservers}) but ntpd is not enabled."
            )
        return ("Non Compliant", "No NTP time servers defined under system/timeservers.")

    def check_session_timeout(self) -> CheckResult:
        """2.1: Ensure Sessions Timeout <= 10 minutes."""
        session_timeout_txt = self.config.findtext(".//system/webgui/session_timeout")
        if session_timeout_txt is not None:
            try:
                val = int(session_timeout_txt)
                if val <= 10:
                    return ("Compliant", f"Session timeout set to {val} minutes.")
                return ("Non Compliant", f"Session timeout set to {val} minutes (> 10).")
            except ValueError:
                return (
                    "Non Compliant",
                    f"session_timeout value '{session_timeout_txt}' is not a valid integer."
                )
        return ("Non Compliant", "No webgui/session_timeout value set in config.xml.")

    def check_auth_servers(self) -> CheckResult:
        """2.2: Ensure LDAP/RADIUS auth server configured."""
        authservers = self.config.findall(".//authserver")
        if authservers:
            names = []
            for a in authservers:
                name = a.findtext("name") or a.findtext("description")
                if name:
                    names.append(name)
            if names:
                return ("Compliant", "Authentication servers configured: " + ", ".join(names))
            return ("Compliant", "Authentication servers configured (names not found in XML).")
        return ("Non Compliant", "No LDAP/RADIUS auth servers (<authserver> blocks) found.")

    def check_snmp_disabled(self) -> CheckResult:
        """3.1: Ensure SNMP is disabled or properly configured."""
        snmp_rocommunity = (self.config.findtext(".//snmpd/rocommunity") or "").strip()
        snmp_pollport = (self.config.findtext(".//snmpd/pollport") or "").strip()

        if not snmp_rocommunity:
            return ("Compliant", "SNMP read-only community is empty; SNMP appears to be disabled.")
        return (
            "Non Compliant",
            f"SNMP rocommunity is configured (pollport {snmp_pollport}). "
            "Verify this meets CIS hardening requirements."
        )

    def check_captive_portal_disabled(self) -> CheckResult:
        """3.2: Ensure Captive Portal is disabled."""
        captiveportal = self.config.find(".//captiveportal")
        has_captive_children = len(captiveportal) > 0 if captiveportal is not None else False

        if has_captive_children:
            return (
                "Non Compliant",
                "Captive portal appears to have configuration present. "
                "Verify if this is required and hardened."
            )
        return ("Compliant", "No captive portal configuration detected.")

    def check_syslog_configured(self) -> CheckResult:
        """6.1: Ensure syslog is configured."""
        remoteserver = (self.config.findtext(".//syslog/remoteserver") or "").strip()

        if remoteserver:
            return ("Compliant", f"Remote syslog server configured: {remoteserver}")
        return ("Non Compliant", "No remote syslog server configured under <syslog><remoteserver>.")

    def check_timezone(self) -> CheckResult:
        """5.2.1: Ensure timezone is configured."""
        timezone = (self.config.findtext(".//system/timezone") or "").strip()
        if timezone:
            return ("Compliant", f"System time zone set to '{timezone}'.")
        return ("Non Compliant", "System time zone is not set under <system><timezone>.")

    def check_dnssec(self) -> CheckResult:
        """5.3.1: Ensure DNSSEC is enabled."""
        unbound = self.config.find("unbound")
        if unbound is not None:
            dnssec = unbound.find("dnssec")
            if dnssec is not None:
                return ("Compliant", "Unbound DNS resolver has DNSSEC enabled.")
            return ("Non Compliant", "Unbound DNS resolver does not have <dnssec /> configured.")
        return ("Not Reviewed", "No <unbound> DNS resolver block found.")

    def check_snmp_traps(self) -> CheckResult:
        """5.1.1 & 5.1.2: SNMP trap configuration."""
        snmp_rocommunity = (self.config.findtext(".//snmpd/rocommunity") or "").strip()
        trapserver = (self.config.findtext(".//snmpd/trapserver") or "").strip()
        trapstring = (self.config.findtext(".//snmpd/trapstring") or "").strip()

        snmpd_conf_text = ""
        if self.ssh:
            try:
                snmpd_conf_text = self.ssh.read_file("/var/net-snmp/snmpd.conf") or ""
                if not snmpd_conf_text:
                    snmpd_conf_text = self.ssh.read_file("/var/etc/snmpd.conf") or ""
            except Exception:
                pass

        has_snmp = bool(snmp_rocommunity) or bool(snmpd_conf_text.strip())

        if not has_snmp:
            return ("Non Applicable", "SNMP appears disabled.")

        trap_conf_found = bool(trapserver or trapstring)
        if snmpd_conf_text:
            if re.search(r"trap[s2]?sink\s+\S+", snmpd_conf_text, re.IGNORECASE) or \
               re.search(r"trapsess\s+.*\s+\S+", snmpd_conf_text, re.IGNORECASE):
                trap_conf_found = True

        if trap_conf_found:
            return ("Compliant", "SNMP trap receiver configuration detected.")
        return ("Non Compliant", "No SNMP trap receiver found in config.xml or snmpd.conf.")

    def check_netsnmp_package(self) -> CheckResult:
        """5.1.3: Ensure NET-SNMP package is used."""
        snmp_rocommunity = (self.config.findtext(".//snmpd/rocommunity") or "").strip()
        installed_pkgs = self.config.find("installedpackages")
        installed_pkgs_text = (
            ET.tostring(installed_pkgs, encoding="unicode").lower()
            if installed_pkgs is not None else ""
        )

        snmpd_conf_exists = False
        if self.ssh:
            snmpd_conf_exists = (
                self.ssh.file_exists("/var/net-snmp/snmpd.conf") or
                self.ssh.file_exists("/var/etc/snmpd.conf")
            )

        if not snmp_rocommunity and not snmpd_conf_exists:
            return ("Non Applicable", "SNMP appears disabled.")

        if "net-snmp" in installed_pkgs_text or snmpd_conf_exists:
            return ("Compliant", "NET-SNMP detected (package entry or snmpd.conf present).")
        return (
            "Non Compliant",
            "SNMP is enabled but NET-SNMP evidence not found in installed packages or config."
        )

    def check_wan_any_destination(self) -> CheckResult:
        """4.1.1: Ensure no WAN rules allow ANY destination."""
        wan_rules = self._get_wan_rules()
        any_dest_rules = []
        for r in wan_rules:
            dest = r.find("destination")
            if dest is not None:
                addr = dest.findtext("network") or dest.findtext("address") or ""
                if addr.strip().lower() == "any":
                    any_dest_rules.append(r)

        if any_dest_rules:
            return ("Non Compliant", f"{len(any_dest_rules)} WAN rule(s) allow ANY destination.")
        return ("Compliant", "No WAN rules allow ANY destination.")

    def check_wan_any_source(self) -> CheckResult:
        """4.1.2: Ensure no WAN rules allow ANY source."""
        wan_rules = self._get_wan_rules()
        any_src_rules = []
        for r in wan_rules:
            src = r.find("source")
            if src is not None:
                addr = src.findtext("network") or src.findtext("address") or ""
                if addr.strip().lower() == "any":
                    any_src_rules.append(r)

        if any_src_rules:
            return ("Non Compliant", f"{len(any_src_rules)} WAN rule(s) allow ANY source.")
        return ("Compliant", "No WAN rules allow ANY source.")

    def check_wan_any_service(self) -> CheckResult:
        """4.1.3: Ensure no WAN rules allow ANY service."""
        wan_rules = self._get_wan_rules()
        any_service_rules = []
        for r in wan_rules:
            proto = (r.findtext("protocol") or "").strip().lower()
            if proto in ("any", "all", ""):
                any_service_rules.append(r)

        if any_service_rules:
            return ("Non Compliant", f"{len(any_service_rules)} WAN rule(s) permit ANY service/protocol.")
        return ("Compliant", "No WAN rules allow ANY service/protocol.")

    def check_wan_disabled_rules(self) -> CheckResult:
        """4.1.4: Ensure no disabled/unused WAN rules exist."""
        wan_rules = self._get_wan_rules()
        disabled_rules = [r for r in wan_rules if r.find("disabled") is not None]

        if disabled_rules:
            return ("Non Compliant", f"{len(disabled_rules)} WAN rule(s) are disabled/unused.")
        return ("Compliant", "No disabled/unused WAN rules found.")

    def check_wan_logging(self) -> CheckResult:
        """4.1.5: Ensure logging is enabled on all WAN rules."""
        wan_rules = self._get_wan_rules()
        no_log_rules = [r for r in wan_rules if r.find("log") is None]

        if no_log_rules:
            return ("Non Compliant", f"{len(no_log_rules)} WAN rule(s) do NOT have logging enabled.")
        return ("Compliant", "All WAN rules have logging enabled.")

    def check_wan_icmp_rules(self) -> CheckResult:
        """4.1.6: Ensure ICMP rules specify types."""
        wan_rules = self._get_wan_rules()
        bad_icmp_rules = []
        for r in wan_rules:
            proto = (r.findtext("protocol") or "").strip().lower()
            if proto == "icmp":
                icmp_type = (r.findtext("icmptype") or "").strip().lower()
                if icmp_type in ("", "any", None):
                    bad_icmp_rules.append(r)

        if bad_icmp_rules:
            return ("Non Compliant", f"{len(bad_icmp_rules)} insecure ICMP rule(s) on WAN.")
        return ("Compliant", "All WAN ICMP rules have specific ICMP types (or none exist).")

    def check_vpn_auth(self) -> CheckResult:
        """5.4.1: Ensure VPN uses RADIUS/LDAP authentication."""
        has_openvpn_server = self.config.find(".//openvpn/openvpn-server") is not None
        has_ipsec_phase1 = self.config.find(".//ipsec/phase1") is not None

        if not (has_openvpn_server or has_ipsec_phase1):
            return ("Non Applicable", "No OpenVPN server or IPsec Phase1 configuration detected.")
        return (
            "Not Reviewed",
            "VPN configuration detected; verify VPN authentication uses RADIUS or LDAP."
        )

    def check_vpn_certificate(self) -> CheckResult:
        """5.4.2: Ensure VPN uses trusted signed certificate."""
        has_openvpn_server = self.config.find(".//openvpn/openvpn-server") is not None
        has_ipsec_phase1 = self.config.find(".//ipsec/phase1") is not None

        if not (has_openvpn_server or has_ipsec_phase1):
            return ("Non Applicable", "No VPN portal configuration detected.")
        return (
            "Not Reviewed",
            "VPN configuration detected; verify a trusted signed certificate is used."
        )

    def check_openvpn_tls(self) -> CheckResult:
        """5.4.3: Ensure OpenVPN TLS encryption settings."""
        has_openvpn_server = self.config.find(".//openvpn/openvpn-server") is not None

        if not has_openvpn_server:
            return ("Non Applicable", "No OpenVPN server configuration detected.")
        return (
            "Not Reviewed",
            "OpenVPN server found; verify TLS encryption settings per CIS benchmark."
        )

    def check_openvpn_cipher(self) -> CheckResult:
        """5.5.1: Ensure OpenVPN cipher and hash algorithms."""
        has_openvpn_server = self.config.find(".//openvpn/openvpn-server") is not None

        if not has_openvpn_server:
            return ("Non Applicable", "No OpenVPN server configuration detected.")
        return (
            "Not Reviewed",
            "OpenVPN server found; verify cipher and hash algorithms per CIS benchmark."
        )

    def _get_wan_rules(self) -> list:
        """Helper to extract WAN firewall rules."""
        filter_elem = self.config.find(".//filter")
        if filter_elem is None:
            return []

        wan_rules = []
        for r in filter_elem.findall("rule"):
            iface = (r.findtext("interface") or "").strip()
            if iface == "wan":
                wan_rules.append(r)

        return wan_rules


# Define check registry - maps control_id to check function
CHECK_REGISTRY: dict[str, Callable[[AutoChecker], CheckResult]] = {
    "1.1": AutoChecker.check_ssh_banner,
    "1.3": AutoChecker.check_motd,
    "1.4": AutoChecker.check_hostname,
    "1.5": AutoChecker.check_dns_servers,
    "1.6": AutoChecker.check_ipv6_disabled,
    "1.8": AutoChecker.check_webgui_https,
    "1.10": AutoChecker.check_ntp_configured,
    "2.1": AutoChecker.check_session_timeout,
    "2.2": AutoChecker.check_auth_servers,
    "3.1": AutoChecker.check_snmp_disabled,
    "3.2": AutoChecker.check_captive_portal_disabled,
    "4.1.1": AutoChecker.check_wan_any_destination,
    "4.1.2": AutoChecker.check_wan_any_source,
    "4.1.3": AutoChecker.check_wan_any_service,
    "4.1.4": AutoChecker.check_wan_disabled_rules,
    "4.1.5": AutoChecker.check_wan_logging,
    "4.1.6": AutoChecker.check_wan_icmp_rules,
    "5.1.1": AutoChecker.check_snmp_traps,
    "5.1.2": AutoChecker.check_snmp_traps,
    "5.1.3": AutoChecker.check_netsnmp_package,
    "5.2.1": AutoChecker.check_timezone,
    "5.3.1": AutoChecker.check_dnssec,
    "5.4.1": AutoChecker.check_vpn_auth,
    "5.4.2": AutoChecker.check_vpn_certificate,
    "5.4.3": AutoChecker.check_openvpn_tls,
    "5.5.1": AutoChecker.check_openvpn_cipher,
    "6.1": AutoChecker.check_syslog_configured,
}
