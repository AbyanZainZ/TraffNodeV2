import os
import json
import time
import asyncio
import socket
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional

import psutil
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, PlainTextResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from checker import ProxyNode, parse_proxies_text, check_all_proxies
from supervisor import NodeSupervisor
from bandwidth import BandwidthTracker, format_bytes
import surfshark

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
PROXIES_PATH = BASE_DIR / "proxies.txt"
NODES_PATH = BASE_DIR / "nodes.json"
STATIC_DIR = BASE_DIR / "static"

DEFAULT_CONFIG = {
    "host": "0.0.0.0",
    "dashboard_port": 8888,
    "traff_token": "",
    "check_timeout": 5.0,
    "max_instances": 1000,
    "auto_heal_interval_seconds": 30,
    "auto_start_on_boot": False,
    "surfshark_private_key": "",
    "surfshark_region": "all",
    "surfshark_node_count": 50,
    "surfshark_start_port": 21000
}

def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                return {**DEFAULT_CONFIG, **cfg}
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(cfg: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

def load_proxies_file() -> str:
    if PROXIES_PATH.exists():
        with open(PROXIES_PATH, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    return ""

def save_proxies_file(content: str):
    with open(PROXIES_PATH, "w", encoding="utf-8") as f:
        f.write(content)

def save_nodes_file(nodes_list: List[ProxyNode]):
    try:
        data = [n.to_dict(include_password=True) for n in nodes_list]
        with open(NODES_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[TraffNode] Error saving nodes.json: {e}")

def load_nodes_file() -> List[ProxyNode]:
    if NODES_PATH.exists():
        try:
            with open(NODES_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            loaded: List[ProxyNode] = []
            for item in data:
                node = ProxyNode(item.get("raw", ""), index=item.get("id", len(loaded) + 1))
                if item.get("password"):
                    node.password = item.get("password")
                node.node_type = item.get("node_type", "proxy")
                node.protocol = item.get("protocol", "HTTP").lower()
                node.proto_specified = item.get("proto_specified", False)
                node.host = item.get("host")
                node.port = item.get("port")
                node.user = item.get("user")
                node.endpoint = item.get("endpoint")
                node.pub_key = item.get("pub_key")
                node.city = item.get("city", "")
                node.country = item.get("country", "Unknown")
                node.exit_ip = item.get("exit_ip")
                node.device_name = item.get("device_name", "")
                node.status = "IDLE"
                node.is_alive = item.get("is_alive", True if node.node_type == "surfshark" else None)
                node.latency_ms = item.get("latency_ms")
                loaded.append(node)
            return loaded
        except Exception as e:
            print(f"[TraffNode] Error loading nodes.json: {e}")
    return []

_cached_public_ip = None

def get_server_ip() -> str:
    global _cached_public_ip
    if _cached_public_ip:
        return _cached_public_ip

    import urllib.request
    endpoints = [
        "https://api.ipify.org",
        "https://ifconfig.me/ip",
        "https://icanhazip.com",
        "https://checkip.amazonaws.com"
    ]
    for url in endpoints:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "curl/7.88.1"})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                detected = resp.read().decode("utf-8").strip()
                if detected and not detected.startswith(("10.", "172.16.", "172.17.", "172.18.", "172.19.", "172.20.", "172.21.", "172.22.", "172.23.", "172.24.", "172.25.", "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.", "192.168.", "127.")):
                    _cached_public_ip = detected
                    return detected
        except Exception:
            pass

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# =============================================================================
# APP STATE: DUAL-POOL ARCHITECTURE (NON-DESTRUCTIVE CONCURRENCY)
# =============================================================================
config = load_config()
supervisor = NodeSupervisor()
bandwidth_tracker = BandwidthTracker()

surfshark_nodes: List[ProxyNode] = []
custom_proxy_nodes: List[ProxyNode] = []
is_checking = False

def get_combined_nodes() -> List[ProxyNode]:
    return surfshark_nodes + custom_proxy_nodes

def find_node_by_id(node_id: int) -> Optional[ProxyNode]:
    for n in surfshark_nodes:
        if n.id == node_id:
            return n
    for n in custom_proxy_nodes:
        if n.id == node_id:
            return n
    return None

async def run_health_check_task():
    global is_checking, custom_proxy_nodes
    if is_checking or not custom_proxy_nodes:
        return
    is_checking = True
    try:
        checked_proxies = await check_all_proxies(
            custom_proxy_nodes,
            max_concurrency=20,
            timeout=config.get("check_timeout", 5.0)
        )
        checked_map = {n.id: n for n in checked_proxies}
        for i, n in enumerate(custom_proxy_nodes):
            if n.id in checked_map:
                custom_proxy_nodes[i] = checked_map[n.id]
        save_nodes_file(get_combined_nodes())
    finally:
        is_checking = False

async def auto_supervisor_loop():
    while True:
        try:
            await asyncio.sleep(config.get("auto_heal_interval_seconds", 30))
            token = config.get("traff_token", "")
            privkey = config.get("surfshark_private_key", "")
            all_nodes = get_combined_nodes()
            if token and all_nodes:
                supervisor.auto_heal_check(all_nodes, token, surfshark_privkey=privkey)
                save_nodes_file(all_nodes)
                for n in all_nodes:
                    if n.pid:
                        bandwidth_tracker.update_proc_traffic(n.pid, n)
        except Exception:
            pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    global surfshark_nodes, custom_proxy_nodes
    saved_nodes = load_nodes_file()
    if saved_nodes:
        surfshark_nodes = [n for n in saved_nodes if getattr(n, "node_type", "proxy") == "surfshark"]
        custom_proxy_nodes = [n for n in saved_nodes if getattr(n, "node_type", "proxy") != "surfshark"]

    # If custom_proxy_nodes is empty, fallback to loading proxies.txt
    if not custom_proxy_nodes:
        raw_text = load_proxies_file()
        if raw_text:
            custom_proxy_nodes = parse_proxies_text(raw_text)
            for idx, p in enumerate(custom_proxy_nodes):
                p.id = 1001 + idx
                p.node_type = "proxy"

    # Start auto-heal loop
    asyncio.create_task(auto_supervisor_loop())

    if custom_proxy_nodes:
        asyncio.create_task(run_health_check_task())

    # Auto start on boot if configured
    token = config.get("traff_token", "")
    if config.get("auto_start_on_boot") and token:
        all_nodes = get_combined_nodes()
        if all_nodes:
            privkey = config.get("surfshark_private_key", "")
            supervisor.start_all(all_nodes, token, surfshark_privkey=privkey)

    yield

    supervisor.stop_all(get_combined_nodes())


app = FastAPI(title="TraffNode V2 — Dual-Engine Hybrid Passive Income", lifespan=lifespan)

STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# =============================================================================
# REQUEST MODELS
# =============================================================================
class ProxiesUpdateRequest(BaseModel):
    raw_text: str
    mode: Optional[str] = "replace"  # "replace" (replaces custom pool only) or "append"

class ConfigUpdateRequest(BaseModel):
    traff_token: str
    dashboard_port: Optional[int] = 8888
    max_instances: Optional[int] = 1000
    surfshark_private_key: Optional[str] = ""
    surfshark_region: Optional[str] = "all"
    surfshark_node_count: Optional[int] = 50
    surfshark_start_port: Optional[int] = 21000

class SurfsharkGenerateRequest(BaseModel):
    private_key: Optional[str] = ""
    region: Optional[str] = "all"
    node_count: Optional[int] = 50
    start_port: Optional[int] = 21000
    mode: Optional[str] = "replace"  # "replace" (replaces surfshark pool only) or "append"


# =============================================================================
# ROUTES
# =============================================================================
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return "<h1>TraffNode V2 is Running</h1><p>static/index.html not found yet.</p>"

@app.get("/api/status")
async def get_status():
    mem = psutil.virtual_memory()
    cpu_pct = psutil.cpu_percent(interval=None)
    bw = bandwidth_tracker.get_system_bandwidth()

    all_nodes = get_combined_nodes()

    running_count = sum(1 for n in all_nodes if n.status == "RUNNING")
    starting_count = sum(1 for n in all_nodes if n.status == "STARTING")
    alive_count = sum(1 for n in all_nodes if n.is_alive is True)
    dead_count = sum(1 for n in all_nodes if n.is_alive is False)

    ss_count = len(surfshark_nodes)
    ss_running = sum(1 for n in surfshark_nodes if n.status == "RUNNING")
    px_count = len(custom_proxy_nodes)
    px_running = sum(1 for n in custom_proxy_nodes if n.status == "RUNNING")

    total_in = sum(n.bytes_in for n in all_nodes)
    total_out = sum(n.bytes_out for n in all_nodes)

    return {
        "status": "online",
        "version": "v2.0-hybrid",
        "server_ip": get_server_ip(),
        "system": {
            "cpu_percent": cpu_pct,
            "ram_used_mb": round(mem.used / (1024 * 1024)),
            "ram_total_mb": round(mem.total / (1024 * 1024)),
            "ram_percent": mem.percent
        },
        "config": {
            "traff_token": config.get("traff_token", ""),
            "dashboard_port": config.get("dashboard_port", 8888),
            "max_instances": config.get("max_instances", 1000),
            "surfshark_private_key": config.get("surfshark_private_key", ""),
            "surfshark_region": config.get("surfshark_region", "all"),
            "surfshark_node_count": config.get("surfshark_node_count", 50),
            "surfshark_start_port": config.get("surfshark_start_port", 21000)
        },
        "metrics": {
            "total_nodes": len(all_nodes),
            "running_nodes": running_count,
            "starting_nodes": starting_count,
            "is_starting_batch": supervisor.is_starting_batch,
            "alive_nodes": alive_count,
            "dead_nodes": dead_count,
            "surfshark_nodes": ss_count,
            "surfshark_running": ss_running,
            "proxy_nodes": px_count,
            "proxy_running": px_running,
            "is_checking": is_checking,
            "bandwidth": {
                "total_bytes_in": total_in or bw["total_recv_bytes"],
                "total_bytes_out": total_out or bw["total_sent_bytes"],
                "speed_down_bps": bw["speed_down_bps"],
                "speed_up_bps": bw["speed_up_bps"],
                "formatted_in": format_bytes(total_in or bw["total_recv_bytes"]),
                "formatted_out": format_bytes(total_out or bw["total_sent_bytes"])
            }
        },
        "nodes": [n.to_dict() for n in all_nodes]
    }

@app.get("/api/surfshark/info")
async def get_surfshark_info():
    all_servers = surfshark.load_servers()
    return {
        "total_servers": len(all_servers),
        "regions": surfshark.PRESET_REGIONS,
        "region_counts": {
            "all": len(all_servers),
            "us": len(surfshark.get_filtered_servers("us")),
            "premium": len(surfshark.get_filtered_servers("premium")),
            "asia": len(surfshark.get_filtered_servers("asia")),
            "europe": len(surfshark.get_filtered_servers("europe"))
        }
    }

@app.post("/api/surfshark/generate")
async def generate_surfshark_nodes(payload: SurfsharkGenerateRequest):
    global surfshark_nodes, config

    if payload.private_key:
        config["surfshark_private_key"] = payload.private_key.strip()
    if payload.region:
        config["surfshark_region"] = payload.region
    if payload.node_count:
        config["surfshark_node_count"] = payload.node_count
    if payload.start_port:
        config["surfshark_start_port"] = payload.start_port
    save_config(config)

    count = max(1, min(config.get("max_instances", 1000), payload.node_count or 50))
    region = payload.region or "all"
    start_port = payload.start_port or 21000

    picked = surfshark.pick_servers(region=region, count=count, shuffle=True)
    if not picked:
        raise HTTPException(status_code=400, detail="Tidak ada server Surfshark ditemukan untuk filter ini.")

    if payload.mode == "replace":
        # Stop existing Surfshark nodes only; NEVER touch custom proxy nodes!
        supervisor.stop_filtered(surfshark_nodes, "surfshark")
        surfshark_nodes = []
        base_id = 1
    else:
        base_id = max([n.id for n in surfshark_nodes] + [0]) + 1

    new_ss_nodes: List[ProxyNode] = []
    for idx, srv in enumerate(picked):
        nid = base_id + idx
        port = start_port + idx
        d = surfshark.create_surfshark_node_dict(nid, srv, port)

        node = ProxyNode(d["raw"], index=nid)
        node.node_type = "surfshark"
        node.protocol = "socks5"
        node.host = "127.0.0.1"
        node.port = port
        node.country = d["country"]
        node.city = d["city"]
        node.endpoint = d["endpoint"]
        node.pub_key = d["pub_key"]
        node.exit_ip = d["exit_ip"]
        node.device_name = d["device_name"]
        node.is_alive = True
        node.status = "IDLE"

        new_ss_nodes.append(node)

    surfshark_nodes.extend(new_ss_nodes)
    save_nodes_file(get_combined_nodes())

    return {
        "success": True,
        "count": len(picked),
        "surfshark_total": len(surfshark_nodes),
        "total_nodes": len(get_combined_nodes()),
        "message": f"🦈 Berhasil men-generate {len(picked)} node Surfshark VPN ({region.upper()})! Custom Proxy tetap aman."
    }

@app.get("/api/proxies/raw", response_class=PlainTextResponse)
async def get_raw_proxies():
    return load_proxies_file()

@app.post("/api/proxies")
async def update_proxies(payload: ProxiesUpdateRequest, bg_tasks: BackgroundTasks):
    global custom_proxy_nodes
    save_proxies_file(payload.raw_text)

    # Stop custom proxy nodes only; NEVER touch Surfshark nodes!
    if payload.mode == "replace":
        supervisor.stop_filtered(custom_proxy_nodes, "proxy")
        custom_proxy_nodes = []
        base_id = 1001
    else:
        base_id = max([n.id for n in custom_proxy_nodes] + [1000]) + 1

    parsed = parse_proxies_text(payload.raw_text)
    for idx, p in enumerate(parsed):
        p.id = base_id + idx
        p.node_type = "proxy"

    custom_proxy_nodes.extend(parsed)
    save_nodes_file(get_combined_nodes())
    bg_tasks.add_task(run_health_check_task)

    return {
        "success": True,
        "count": len(parsed),
        "proxy_total": len(custom_proxy_nodes),
        "total_nodes": len(get_combined_nodes()),
        "message": f"🌐 Berhasil memuat {len(parsed)} proxy node! Surfshark nodes tetap aman & tidak tertimpa."
    }

@app.post("/api/config")
async def update_config(payload: ConfigUpdateRequest):
    global config
    config["traff_token"] = payload.traff_token.strip()
    if payload.dashboard_port:
        config["dashboard_port"] = max(1024, min(65000, payload.dashboard_port))
    if payload.max_instances:
        config["max_instances"] = max(1, min(2500, payload.max_instances))
    if payload.surfshark_private_key is not None:
        config["surfshark_private_key"] = payload.surfshark_private_key.strip()
    if payload.surfshark_region:
        config["surfshark_region"] = payload.surfshark_region
    if payload.surfshark_node_count:
        config["surfshark_node_count"] = payload.surfshark_node_count
    if payload.surfshark_start_port:
        config["surfshark_start_port"] = payload.surfshark_start_port

    save_config(config)
    return {"success": True, "config": config, "message": "Konfigurasi token & Surfshark berhasil disimpan!"}

@app.post("/api/check")
async def trigger_check(bg_tasks: BackgroundTasks):
    global is_checking
    if is_checking:
        return {"success": False, "message": "Pengecekan proxy sedang berlangsung."}
    bg_tasks.add_task(run_health_check_task)
    return {"success": True, "message": "Pengecekan kesehatan custom proxy dimulai!"}

# =============================================================================
# SELECTIVE CONTROLS (START / STOP / RESTART)
# =============================================================================
@app.post("/api/start-all")
async def start_all_nodes():
    token = config.get("traff_token", "")
    privkey = config.get("surfshark_private_key", "")
    if not token:
        raise HTTPException(status_code=400, detail="Token TraffMonetizer belum diisi di konfigurasi!")
    all_nodes = get_combined_nodes()
    if not all_nodes:
        raise HTTPException(status_code=400, detail="Belum ada node yang siap dijalankan!")

    to_start = [n for n in all_nodes if n.status != "RUNNING"]
    for n in to_start:
        n.status = "STARTING"
    save_nodes_file(all_nodes)

    # Launch staggered background startup with 0.6s pacing so VPS CPU/IO does not freeze or lag
    asyncio.create_task(
        supervisor.start_nodes_staggered(
            to_start,
            token,
            surfshark_privkey=privkey,
            delay=0.6,
            save_callback=lambda: save_nodes_file(all_nodes)
        )
    )

    return {
        "success": True,
        "started": len(to_start),
        "message": f"🚀 Memulai {len(to_start)} worker secara bertahap (smooth pacing 0.6s) agar VPS tidak lag!"
    }

@app.post("/api/start-surfshark")
async def start_surfshark_only():
    token = config.get("traff_token", "")
    privkey = config.get("surfshark_private_key", "")
    if not token:
        raise HTTPException(status_code=400, detail="Token TraffMonetizer belum diisi di konfigurasi!")
    if not privkey:
        raise HTTPException(status_code=400, detail="WireGuard Private Key Surfshark belum diisi!")
    if not surfshark_nodes:
        raise HTTPException(status_code=400, detail="Belum ada node Surfshark yang di-generate!")

    to_start = [n for n in surfshark_nodes if n.status != "RUNNING"]
    for n in to_start:
        n.status = "STARTING"
    save_nodes_file(get_combined_nodes())

    asyncio.create_task(
        supervisor.start_nodes_staggered(
            to_start,
            token,
            surfshark_privkey=privkey,
            delay=0.6,
            save_callback=lambda: save_nodes_file(get_combined_nodes())
        )
    )

    return {
        "success": True,
        "started": len(to_start),
        "message": f"🦈 Memulai {len(to_start)} worker Surfshark secara bertahap (smooth pacing 0.6s)!"
    }

@app.post("/api/start-proxies")
async def start_proxies_only():
    token = config.get("traff_token", "")
    if not token:
        raise HTTPException(status_code=400, detail="Token TraffMonetizer belum diisi di konfigurasi!")
    if not custom_proxy_nodes:
        raise HTTPException(status_code=400, detail="Belum ada custom proxy yang disimpan!")

    to_start = [n for n in custom_proxy_nodes if n.status != "RUNNING"]
    for n in to_start:
        n.status = "STARTING"
    save_nodes_file(get_combined_nodes())

    asyncio.create_task(
        supervisor.start_nodes_staggered(
            to_start,
            token,
            delay=0.6,
            save_callback=lambda: save_nodes_file(get_combined_nodes())
        )
    )

    return {
        "success": True,
        "started": len(to_start),
        "message": f"🌐 Memulai {len(to_start)} worker Custom Proxy secara bertahap (smooth pacing 0.6s)!"
    }

@app.post("/api/stop-all")
async def stop_all_nodes():
    all_nodes = get_combined_nodes()
    stopped = await asyncio.to_thread(supervisor.stop_all, all_nodes)
    save_nodes_file(all_nodes)
    return {"success": True, "stopped": stopped, "message": "Seluruh worker node (Surfshark + Proxy) telah dihentikan."}

@app.post("/api/stop-surfshark")
async def stop_surfshark_only():
    stopped = await asyncio.to_thread(supervisor.stop_filtered, surfshark_nodes, "surfshark")
    save_nodes_file(get_combined_nodes())
    return {"success": True, "stopped": stopped, "message": f"🦈 {stopped} worker Surfshark telah dihentikan."}

@app.post("/api/stop-proxies")
async def stop_proxies_only():
    stopped = await asyncio.to_thread(supervisor.stop_filtered, custom_proxy_nodes, "proxy")
    save_nodes_file(get_combined_nodes())
    return {"success": True, "stopped": stopped, "message": f"🌐 {stopped} worker Custom Proxy telah dihentikan."}

@app.post("/api/restart-all")
async def restart_all_nodes():
    token = config.get("traff_token", "")
    privkey = config.get("surfshark_private_key", "")
    if not token:
        raise HTTPException(status_code=400, detail="Token TraffMonetizer belum diisi!")
    all_nodes = get_combined_nodes()
    await asyncio.to_thread(supervisor.stop_all, all_nodes)
    await asyncio.sleep(0.5)
    started = await asyncio.to_thread(supervisor.start_all, all_nodes, token, surfshark_privkey=privkey)
    save_nodes_file(all_nodes)
    return {"success": True, "started": started, "message": f"Semua {started} node berhasil di-restart!"}

@app.delete("/api/nodes/surfshark")
async def clear_surfshark_pool():
    global surfshark_nodes
    supervisor.stop_filtered(surfshark_nodes, "surfshark")
    count = len(surfshark_nodes)
    surfshark_nodes = []
    save_nodes_file(get_combined_nodes())
    return {"success": True, "cleared": count, "message": f"🦈 {count} node Surfshark berhasil dihapus dari pool."}

@app.delete("/api/nodes/proxies")
async def clear_proxy_pool():
    global custom_proxy_nodes
    supervisor.stop_filtered(custom_proxy_nodes, "proxy")
    count = len(custom_proxy_nodes)
    custom_proxy_nodes = []
    save_proxies_file("")
    save_nodes_file(get_combined_nodes())
    return {"success": True, "cleared": count, "message": f"🌐 {count} node Custom Proxy berhasil dihapus dari pool."}

# =============================================================================
# SINGLE NODE OPERATIONS
# =============================================================================
@app.post("/api/node/{node_id}/start")
async def start_single_node(node_id: int):
    token = config.get("traff_token", "")
    privkey = config.get("surfshark_private_key", "")
    node = find_node_by_id(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node tidak ditemukan")
    ok = supervisor.start_node(node, token, surfshark_privkey=privkey)
    if not ok:
        raise HTTPException(status_code=500, detail=node.error or "Gagal menjalankan node")
    save_nodes_file(get_combined_nodes())
    return {"success": True, "node": node.to_dict()}

@app.post("/api/node/{node_id}/stop")
async def stop_single_node(node_id: int):
    node = find_node_by_id(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node tidak ditemukan")
    supervisor.stop_node(node)
    save_nodes_file(get_combined_nodes())
    return {"success": True, "node": node.to_dict()}

@app.post("/api/node/{node_id}/restart")
async def restart_single_node(node_id: int):
    token = config.get("traff_token", "")
    privkey = config.get("surfshark_private_key", "")
    node = find_node_by_id(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node tidak ditemukan")
    ok = supervisor.restart_node(node, token, surfshark_privkey=privkey)
    if not ok:
        raise HTTPException(status_code=500, detail=node.error or "Gagal restart node")
    save_nodes_file(get_combined_nodes())
    return {"success": True, "node": node.to_dict()}

@app.get("/api/node/{node_id}/logs", response_class=PlainTextResponse)
async def get_node_logs(node_id: int):
    node = find_node_by_id(node_id)
    if not node:
        return "Node tidak ditemukan."
    return supervisor.get_node_logs(node)


if __name__ == "__main__":
    import uvicorn
    cfg = load_config()
    port = cfg.get("dashboard_port", 8888)
    print(f"⚡ TraffNode V2 Dashboard starting on http://{cfg.get('host', '0.0.0.0')}:{port}")
    uvicorn.run("app:app", host=cfg.get("host", "0.0.0.0"), port=port, reload=False)
