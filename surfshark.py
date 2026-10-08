import os
import json
import random
import socket
from pathlib import Path
from typing import List, Dict, Any, Optional

BASE_DIR = Path(__file__).resolve().parent
SERVERS_FILE = BASE_DIR / "surfshark_servers.json"

_SERVERS_CACHE: List[Dict[str, Any]] = []
_DNS_CACHE: Dict[str, str] = {}

PRESET_REGIONS = {
    "all": "Semua Negara (Acak Global - 925 Server Fisik Unik)",
    "us": "United States (215 Server Fisik US Unik)",
    "premium": "Negara Premium (US, UK, DE, SG, JP, AU, CA, NL)",
    "asia": "Asia Pasifik (SG, MY, ID, JP, KR, HK, TW, AU, TH, VN, PH, NZ)",
    "europe": "Eropa (DE, UK, NL, FR, IT, ES, CH, PL, SE, NO, BE)"
}

US_COUNTRIES = {"United States"}

PREMIUM_COUNTRIES = {
    "United States", "United Kingdom", "Germany", "Singapore",
    "Japan", "Australia", "Canada", "Netherlands"
}

ASIA_COUNTRIES = {
    "Singapore", "Malaysia", "Indonesia", "Japan", "South Korea",
    "Hong Kong", "Taiwan", "Australia", "Thailand", "Vietnam", "Philippines", "New Zealand"
}

EUROPE_COUNTRIES = {
    "Germany", "United Kingdom", "Netherlands", "France",
    "Italy", "Spain", "Switzerland", "Poland", "Sweden", "Norway", "Belgium"
}

def load_servers(force_reload: bool = False) -> List[Dict[str, Any]]:
    global _SERVERS_CACHE
    if _SERVERS_CACHE and not force_reload:
        return _SERVERS_CACHE

    if SERVERS_FILE.exists():
        try:
            with open(SERVERS_FILE, "r", encoding="utf-8") as f:
                _SERVERS_CACHE = json.load(f)
                return _SERVERS_CACHE
        except Exception as e:
            print(f"[Surfshark] Gagal membaca {SERVERS_FILE}: {e}")

    return []

def get_filtered_servers(region: str = "all") -> List[Dict[str, Any]]:
    servers = load_servers()
    if not servers:
        return []

    r = (region or "all").lower()
    if r == "us":
        filtered = [s for s in servers if s.get("country") in US_COUNTRIES]
    elif r == "premium":
        filtered = [s for s in servers if s.get("country") in PREMIUM_COUNTRIES]
    elif r == "asia":
        filtered = [s for s in servers if s.get("country") in ASIA_COUNTRIES]
    elif r == "europe":
        filtered = [s for s in servers if s.get("country") in EUROPE_COUNTRIES]
    else:
        filtered = list(servers)

    return filtered if filtered else servers

def pick_servers(region: str = "all", count: int = 50, shuffle: bool = True) -> List[Dict[str, Any]]:
    pool = get_filtered_servers(region)
    if not pool:
        return []

    pool_list = list(pool)
    if shuffle:
        random.shuffle(pool_list)

    # Prioritize 0 duplicate physical IPs
    if count <= len(pool_list):
        return [s.copy() for s in pool_list[:count]]

    # If count exceeds pool, cycle through
    results = []
    for i in range(count):
        server = pool_list[i % len(pool_list)]
        results.append(server.copy())
    return results

def resolve_endpoint_ip(domain_or_endpoint: str) -> str:
    domain = domain_or_endpoint.split(":")[0].strip()
    if domain in _DNS_CACHE:
        return _DNS_CACHE[domain]
    try:
        ip = socket.gethostbyname(domain)
        _DNS_CACHE[domain] = ip
        return ip
    except Exception:
        return domain

def create_surfshark_node_dict(
    nid: int,
    server: Dict[str, Any],
    port: int
) -> Dict[str, Any]:
    pub_key = server.get("pubkey") or server.get("pubKey") or ""
    server_ip = server.get("ip")
    endpoint = server.get("endpoint") or f"{server_ip}:{server.get('port', 51820)}"

    if not server_ip:
        domain = endpoint.split(":")[0]
        server_ip = resolve_endpoint_ip(domain)

    country = server.get("country", "Unknown")
    city = server.get("city", "")
    dev_name = f"{country} - {server_ip}"

    return {
        "id": nid,
        "node_type": "surfshark",
        "raw": f"surfshark://{endpoint}#{country}-{city}",
        "protocol": "SOCKS5",
        "host": "127.0.0.1",
        "port": port,
        "user": None,
        "password": None,
        "country": country,
        "city": city,
        "endpoint": endpoint,
        "pub_key": pub_key,
        "exit_ip": server_ip,
        "device_name": dev_name,
        "is_alive": True,
        "latency_ms": 0.0,
        "error": None,
        "last_checked": None,
        "status": "IDLE",
        "pid": None,
        "started_at": None,
        "bytes_in": 0,
        "bytes_out": 0
    }
