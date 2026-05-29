"""FastAPI wrapper for DashboardServer — provides HTTP API + WebSocket streaming."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from .metrics import DashboardMetrics
from .server import DashboardServer


class WebSocketClient:
    """Adapter to make FastAPI WebSocket look like DashboardServer client."""

    def __init__(self, websocket: WebSocket) -> None:
        self._ws = websocket

    async def send_text(self, message: str) -> None:
        await self._ws.send_text(message)

    async def send(self, message: str) -> None:
        await self._ws.send_text(message)


class DashboardWebServer:
    """FastAPI + WebSocket server wrapping DashboardServer."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8765) -> None:
        self.metrics = DashboardMetrics()
        self.server = DashboardServer(self.metrics, host=host, port=port)
        self.app = FastAPI(title="ROSClaw Dashboard", version="1.0.0")
        self._setup_routes()

    def attach_to_event_bus(self, event_bus: Any) -> None:
        """Subscribe to episode/praxis events for live metrics updates."""
        self.server.attach_to_event_bus(event_bus)

        # Subscribe to episode completion events
        def on_episode_complete(event: Any) -> None:
            payload = getattr(event, "payload", {})
            episode_id = payload.get("episode_id", "unknown")
            robot_id = payload.get("robot_id", "unknown")
            success = payload.get("success", False)
            duration = payload.get("duration_sec")
            self.metrics.record_episode(
                episode_id=episode_id,
                robot_id=robot_id,
                status="success" if success else "failed",
                reward=1.0 if success else 0.0,
                duration_sec=duration,
            )

        event_bus.subscribe("praxis.completed", on_episode_complete)
        event_bus.subscribe("rosclaw.sandbox.episode.finished", on_episode_complete)

    def _setup_routes(self) -> None:
        @self.app.get("/health")
        async def health() -> dict[str, Any]:
            return self.server.get_health()

        @self.app.get("/snapshot")
        async def snapshot() -> dict[str, Any]:
            return self.server.get_snapshot()

        @self.app.get("/events/counts")
        async def event_counts() -> dict[str, int]:
            return self.metrics.get_event_counts()

        @self.app.get("/metrics/provider")
        async def provider_metrics() -> dict[str, Any]:
            return self.metrics.get_provider_stats()

        @self.app.get("/metrics/sandbox")
        async def sandbox_metrics() -> dict[str, Any]:
            return self.metrics.get_sandbox_stats()

        @self.app.get("/metrics/episode")
        async def episode_metrics() -> dict[str, Any]:
            return self.metrics.get_episode_stats()

        @self.app.post("/metrics/provider")
        async def record_provider(
            provider: str, capability: str, latency_ms: float, status: str
        ) -> dict[str, str]:
            self.metrics.record_provider_call(provider, capability, latency_ms, status)
            return {"status": "recorded"}

        @self.app.post("/metrics/sandbox")
        async def record_sandbox(
            action_type: str, is_safe: bool, violations: list[str] | None = None
        ) -> dict[str, str]:
            self.metrics.record_sandbox_validation(action_type, is_safe, violations)
            return {"status": "recorded"}

        @self.app.post("/metrics/episode")
        async def record_episode(
            episode_id: str,
            robot_id: str,
            status: str,
            reward: float | None = None,
            duration_sec: float | None = None,
        ) -> dict[str, str]:
            self.metrics.record_episode(episode_id, robot_id, status, reward, duration_sec)
            return {"status": "recorded"}

        @self.app.post("/event/{topic}")
        async def record_event(topic: str) -> dict[str, str]:
            self.metrics.increment_event(topic)
            return {"status": "recorded"}

        @self.app.post("/health/{module}")
        async def set_module_health(module: str, status: str) -> dict[str, str]:
            self.metrics.set_module_health(module, status)
            return {"status": "updated"}

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket) -> None:
            await websocket.accept()
            client = WebSocketClient(websocket)
            self.server.register_client(client)
            try:
                # Send initial snapshot
                snapshot = self.server.get_snapshot()
                await websocket.send_text(json.dumps({"type": "snapshot", "data": snapshot}))
                # Keep connection alive and handle incoming messages
                while True:
                    msg = await websocket.receive_text()
                    data = json.loads(msg)
                    if data.get("type") == "ping":
                        await websocket.send_text(json.dumps({"type": "pong"}))
            except WebSocketDisconnect:
                pass
            finally:
                self.server.unregister_client(client)

    async def start(self) -> None:
        await self.server.start()

    async def stop(self) -> None:
        await self.server.stop()


# FastAPI app instance for uvicorn
_metrics = DashboardMetrics()
_server = DashboardWebServer()
app = _server.app


async def main() -> None:
    ws = DashboardWebServer()
    await ws.start()
    print("DashboardWebServer started on http://0.0.0.0:8765")
    print("WebSocket: ws://localhost:8765/ws")
    print("Health: http://localhost:8765/health")
    print("Snapshot: http://localhost:8765/snapshot")
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        await ws.stop()
        print("DashboardWebServer stopped")


if __name__ == "__main__":
    asyncio.run(main())
