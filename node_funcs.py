import re


def get_valid_node_name(name):
    name = bytes(name, 'utf-8').decode('utf-8', 'ignore')
    return re.sub(r"[<>`~!@#$%^&*(){}[\]?/\\;:\"']+", "", name)


def device_address(mac_address):
    """Stable IoX address from Flo device MAC (12 hex chars)."""
    return str(mac_address).lower().replace(':', '')[:14]
