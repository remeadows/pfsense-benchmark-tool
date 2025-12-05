def check_webgui_https(config_xml):
    # extract <webgui><protocol>
    protocol = config_xml.findtext(".//webgui/protocol")
    if protocol and protocol.lower() == "https":
        return ("Compliant", "WebConfigurator is set to HTTPS")
    return ("Non Compliant", "WebConfigurator is NOT set to HTTPS")

def check_dns_servers(config_xml):
    dns_servers = config_xml.findall(".//system/dnsserver")
    if len(dns_servers) > 0:
        return ("Compliant", f"DNS servers found: {len(dns_servers)}")
    return ("Non Compliant", "No DNS servers configured")

def check_ipv6(config_xml):
    proto = config_xml.findtext(".//interfaces/wan/ipprotocol")
    if proto == "ipv4":
        return ("Compliant", "IPv6 is disabled")
    return ("Non Compliant", "IPv6 enabled")
