"""Prove /health stays responsive while an audit runs off the event loop."""

from __future__ import annotations

import socket
import threading
import time

import httpx
import uvicorn


def test_health_stays_responsive_during_audit(monkeypatch):
    import app.api as api
    import app.services.audits as audits

    original = audits.execute_audit

    def slow(run_id: str) -> None:
        time.sleep(1.2)
        original(run_id)

    monkeypatch.setattr(api, "execute_audit", slow)

    from app.main import app

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{port}"
    try:
        deadline = time.time() + 15
        while time.time() < deadline:
            try:
                httpx.get(f"{base}/ready", timeout=0.5).raise_for_status()
                break
            except (httpx.HTTPError, OSError):
                time.sleep(0.1)
        else:
            raise AssertionError("server did not become ready")

        with httpx.Client(base_url=base, timeout=30) as http:
            created = http.post(
                "/api/datasets/synthetic",
                json={"profile": "similar_accuracy_different_errors"},
            )
            created.raise_for_status()
            dataset_id = created.json()["id"]

            holder: dict = {}

            def post_audit() -> None:
                with httpx.Client(base_url=base, timeout=30) as other:
                    holder["response"] = other.post(
                        "/api/audits",
                        json={"dataset_id": dataset_id, "bootstrap_iterations": 20},
                    )

            worker = threading.Thread(target=post_audit)
            worker.start()
            time.sleep(0.4)
            started = time.perf_counter()
            health = http.get("/health")
            elapsed = time.perf_counter() - started
            assert health.status_code == 200
            assert health.json()["status"] == "ok"
            assert elapsed < 0.7
            worker.join(timeout=30)
            assert holder["response"].status_code == 200
    finally:
        server.should_exit = True
        thread.join(timeout=5)
