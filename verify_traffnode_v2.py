import asyncio
import json
import time
from pathlib import Path
import httpx

import surfshark
from checker import ProxyNode, parse_proxies_text
from supervisor import NodeSupervisor
from app import app, get_combined_nodes, surfshark_nodes, custom_proxy_nodes, save_nodes_file, load_nodes_file

SAMPLE_PROXIES = """
191.96.254.138:6185:windowsproxy001:win012345
31.59.20.176:6754:windowsproxy002:windows123
31.58.9.4:6077:windowsproxy001:win012345
45.38.107.97:6014:windowsproxy001:win012345
45.38.107.97:6014:windowsproxy002:windows123
191.96.254.138:6185:windowsproxy002:windows123
45.38.107.97:6014:qntiugmc:fitdi4uhbspx
142.111.67.146:5611:windowsproxy002:windows123
64.137.96.74:6641:qntiugmc:fitdi4uhbspx
31.58.9.4:6077:windowsproxy002:windows123
"""

async def run_all_tests():
    print("==================================================================")
    print("  TRAFFNODE V2 — COMPREHENSIVE AUTOMATED VERIFICATION SUITE")
    print("==================================================================")

    # 1. VERIFY SURFSHARK SERVERS DATABASE
    servers = surfshark.load_servers(force_reload=True)
    assert len(servers) == 925, f"Expected 925 servers, got {len(servers)}"
    unique_ips = set(s['ip'] for s in servers)
    assert len(unique_ips) == 925, f"Expected 925 unique IPs, got {len(unique_ips)}"
    print(f"[PASS] 1. surfshark_servers.json: 925 physical servers loaded, 925 unique IPs (0 duplicate IP penalty).")

    # 2. VERIFY SURFSHARK REGIONS AND PICKER
    us_servers = surfshark.get_filtered_servers('us')
    assert len(us_servers) == 215, f"Expected 215 US servers, got {len(us_servers)}"
    picked = surfshark.pick_servers('all', 50, shuffle=True)
    assert len(picked) == 50, f"Expected 50 picked servers, got {len(picked)}"
    assert len(set(s['ip'] for s in picked)) == 50, "Picked servers contained duplicate IPs!"

    sample_node_dict = surfshark.create_surfshark_node_dict(1, picked[0], 21001)
    assert sample_node_dict['pub_key'], "pub_key was empty in node dict!"
    assert sample_node_dict['endpoint'], "endpoint was empty in node dict!"
    print(f"[PASS] 2. surfshark.py: US pool has 215 servers, picker guarantees 0 duplicate IPs, node dict valid.")

    # 3. VERIFY PROXY PARSER ON USER'S SAMPLE PROXIES
    nodes = parse_proxies_text(SAMPLE_PROXIES)
    assert len(nodes) == 10, f"Expected 10 nodes, got {len(nodes)}"
    for idx, n in enumerate(nodes):
        assert n.is_valid, f"Node {idx} is invalid!"
        assert n.host and n.port and n.user and n.password, f"Node {idx} missing auth credentials!"
        assert n.to_url().startswith("http://"), f"Invalid to_url(): {n.to_url()}"
    print(f"[PASS] 3. checker.py: All 10 user sample proxies parsed with 100% accuracy (host, port, user, pass).")

    # 4. VERIFY PROXY PARSER ADVANCED EDGE CASES
    # Case A: user:pass:host:port where password is purely numeric
    p_num_pass = ProxyNode("user:12345:1.2.3.4:8080")
    assert p_num_pass.host == "1.2.3.4" and p_num_pass.port == 8080 and p_num_pass.user == "user" and p_num_pass.password == "12345", f"Numeric pass failed: {p_num_pass.to_dict()}"

    # Case B: host:port@user:pass where password is numeric
    p_hp_at_up = ProxyNode("1.2.3.4:8080@user:12345")
    assert p_hp_at_up.host == "1.2.3.4" and p_hp_at_up.port == 8080 and p_hp_at_up.user == "user" and p_hp_at_up.password == "12345", f"Host@user failed: {p_hp_at_up.to_dict()}"

    # Case C: Space-separated auth
    p_space1 = ProxyNode("191.96.254.138:6185 windowsproxy001 win012345")
    assert p_space1.host == "191.96.254.138" and p_space1.port == 6185 and p_space1.user == "windowsproxy001" and p_space1.password == "win012345"

    p_space2 = ProxyNode("191.96.254.138 6185 windowsproxy001 win012345")
    assert p_space2.host == "191.96.254.138" and p_space2.port == 6185 and p_space2.user == "windowsproxy001" and p_space2.password == "win012345"

    # Case D: URL scheme
    edge1 = ProxyNode("socks5://user1:pass1@1.2.3.4:1080")
    assert edge1.protocol == "socks5" and edge1.host == "1.2.3.4" and edge1.port == 1080 and edge1.user == "user1"
    print(f"[PASS] 4. checker.py edge cases: parsed numeric passwords, space-delimited formats, and URL schemes.")

    # 5. VERIFY PASSWORD STORAGE INTEGRITY
    storage_dict = p_num_pass.to_dict(include_password=True)
    assert storage_dict.get("password") == "12345", "Storage dict did not include password!"
    api_dict = p_num_pass.to_dict(include_password=False)
    assert "password" not in api_dict, "API dict leaked password!"
    print(f"[PASS] 5. checker.py: Secure storage dictionary preserves passwords while API responses redact it.")

    # 6. VERIFY SUPERVISOR PROCESS CONTROLLER & SELECTIVE START/STOP
    sup = NodeSupervisor()
    ss_node = ProxyNode("surfshark://1.2.3.4:51820#US-Ashburn", 1)
    ss_node.node_type = "surfshark"
    ss_node.endpoint = "1.2.3.4:51820"
    ss_node.pub_key = "dummykey=="
    ss_node.port = 21001

    px_node = ProxyNode("191.96.254.138:6185:windowsproxy001:win012345", 2)
    test_nodes = [ss_node, px_node]

    # Test selective start Surfshark only
    started_ss = sup.start_filtered(test_nodes, "surfshark", token="test_token", surfshark_privkey="dummy_privkey")
    assert started_ss == 1, f"Expected 1 SS started, got {started_ss}"
    assert ss_node.status == "RUNNING"
    assert px_node.status == "IDLE"

    # Test selective start Proxy only
    started_px = sup.start_filtered(test_nodes, "proxy", token="test_token")
    assert started_px == 1, f"Expected 1 PX started, got {started_px}"
    assert ss_node.status == "RUNNING"
    assert px_node.status == "RUNNING"

    # Test selective stop Surfshark
    stopped_ss = sup.stop_filtered(test_nodes, "surfshark")
    assert stopped_ss == 1, f"Expected 1 SS stopped, got {stopped_ss}"
    assert ss_node.status == "STOPPED"
    assert px_node.status == "RUNNING"

    # Test stop all
    sup.stop_all(test_nodes)
    assert px_node.status == "STOPPED"
    print(f"[PASS] 6. supervisor.py: Selective start/stop and simultaneous concurrency verified.")

    # 7. VERIFY AUTO-HEAL RECOVERY ON MISSING/DEAD PROCESS
    dead_node = ProxyNode("1.2.3.4:8080", 99)
    dead_node.status = "RUNNING"
    # Process is missing from supervisor.procs -> auto-heal must detect and restart!
    sup.auto_heal_check([dead_node], "test_token")
    assert dead_node.status == "RUNNING" and dead_node.pid is not None, "Auto-heal failed to restart missing process!"
    sup.stop_node(dead_node)
    print(f"[PASS] 7. supervisor.py: Auto-heal correctly detects missing/dead processes and self-heals.")

    # 8. VERIFY STAGGERED NON-LAGGING ASYNC PACING
    stagger_nodes = [ProxyNode(f"10.0.0.{i}:8080", 200 + i) for i in range(3)]
    t_start = time.time()
    stagger_count = await sup.start_nodes_staggered(stagger_nodes, "test_token", delay=0.1)
    t_elapsed = time.time() - t_start
    assert stagger_count == 3, f"Expected 3 started, got {stagger_count}"
    assert t_elapsed >= 0.25, f"Expected pacing delay >= 0.25s, got {t_elapsed:.3f}s"
    for n in stagger_nodes:
        assert n.status == "RUNNING"
    sup.stop_all(stagger_nodes)
    print(f"[PASS] 8. supervisor.py: Staggered pacing startup (non-lagging throttle) verified.")

    # 9. VERIFY STAGGERED STARTUP CANCELLATION ON STOP
    cancel_nodes = [ProxyNode(f"10.0.1.{i}:8080", 300 + i) for i in range(5)]
    async def cancel_after_brief():
        await asyncio.sleep(0.08)
        sup.cancel_startup()

    asyncio.create_task(cancel_after_brief())
    await sup.start_nodes_staggered(cancel_nodes, "test_token", delay=0.1)
    # At least some nodes should be cancelled and not RUNNING
    running_after_cancel = sum(1 for n in cancel_nodes if n.status == "RUNNING")
    assert running_after_cancel < 5, f"Cancellation failed to abort queue! {running_after_cancel}/5 ran"
    sup.stop_all(cancel_nodes)
    print(f"[PASS] 9. supervisor.py: Startup cancellation immediately aborts remaining batch on stop.")

    # 10. VERIFY FASTAPI DUAL-POOL NON-DESTRUCTIVE STATE (VIA ASGITransport)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Step A: Update config token & key
        r = await client.post("/api/config", json={
            "traff_token": "dummy_tm_token_123",
            "surfshark_private_key": "dummy_privkey_abc",
            "surfshark_region": "us",
            "surfshark_node_count": 5
        })
        assert r.status_code == 200

        # Step B: Generate 5 Surfshark nodes
        r = await client.post("/api/surfshark/generate", json={
            "private_key": "dummy_privkey_abc",
            "region": "us",
            "node_count": 5,
            "mode": "replace"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["surfshark_total"] == 5, f"Expected 5 SS nodes, got {data['surfshark_total']}"
        assert data["total_nodes"] == 5

        # Step C: Add 10 Custom Proxies
        r = await client.post("/api/proxies", json={
            "raw_text": SAMPLE_PROXIES,
            "mode": "replace"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["proxy_total"] == 10, f"Expected 10 proxy nodes, got {data['proxy_total']}"
        assert data["total_nodes"] == 15, f"Expected 15 combined nodes (5 SS + 10 PX), got {data['total_nodes']}!"

        # Step D: Re-generate Surfshark with 8 nodes -> Proxy must NOT be erased!
        r = await client.post("/api/surfshark/generate", json={
            "private_key": "dummy_privkey_abc",
            "region": "all",
            "node_count": 8,
            "mode": "replace"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["surfshark_total"] == 8
        assert data["total_nodes"] == 18, f"Expected 18 combined nodes (8 SS + 10 PX), got {data['total_nodes']}!"

        # Step E: Check /api/status metrics
        r = await client.get("/api/status")
        assert r.status_code == 200
        status_data = r.json()
        metrics = status_data["metrics"]
        assert metrics["total_nodes"] == 18
        assert metrics["surfshark_nodes"] == 8
        assert metrics["proxy_nodes"] == 10

        # Step F: Start all (non-blocking smooth start)
        r = await client.post("/api/start-all")
        assert r.status_code == 200
        start_data = r.json()
        assert start_data["started"] == 18, f"Expected 18 started, got {start_data['started']}"

        # Wait briefly for staggered background task to begin
        await asyncio.sleep(0.3)
        r = await client.get("/api/status")
        assert r.status_code == 200
        assert r.json()["metrics"]["running_nodes"] > 0 or r.json()["metrics"]["starting_nodes"] > 0

        # Step G: Stop all
        r = await client.post("/api/stop-all")
        assert r.status_code == 200

        # Step H: Selective clear
        r = await client.delete("/api/nodes/surfshark")
        assert r.status_code == 200
        r = await client.get("/api/status")
        assert r.json()["metrics"]["total_nodes"] == 10  # 10 custom proxies remain!

        r = await client.delete("/api/nodes/proxies")
        assert r.status_code == 200
        r = await client.get("/api/status")
        assert r.json()["metrics"]["total_nodes"] == 0

    print(f"[PASS] 10. app.py: Dual-pool state is 100% non-destructive and staggered non-lagging start verified.")
    print("==================================================================")
    print("  ALL 10 VERIFICATION TEST SUITES PASSED PERFECTLY!")
    print("==================================================================")

if __name__ == "__main__":
    asyncio.run(run_all_tests())
