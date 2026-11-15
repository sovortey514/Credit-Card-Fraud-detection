"""Integration tests for chronological replay delivery."""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_sse_replay_emits_ordered_scored_events():
    with client.stream("GET", "/api/v1/replay/stream?speed=250&model=random_forest&limit=3") as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())
    assert body.count("event: scored") == 3
    assert "id: 0" in body and "id: 1" in body and "id: 2" in body


def test_websocket_burst_has_zero_dropped_messages():
    received = []
    with client.websocket_connect("/api/v1/replay/ws") as websocket:
        websocket.send_json({"speed": 250, "model": "random_forest", "limit": 5})
        for expected_sequence in range(5):
            event = websocket.receive_json()
            received.append(event["sequence"])
            assert event["sequence"] == expected_sequence
            websocket.send_json({"type": "ack", "sequence": event["sequence"]})
        complete = websocket.receive_json()
    assert received == list(range(5))
    assert complete == {"type": "complete", "emitted": 5, "acknowledged": 5, "dropped": 0}


def test_replay_rejects_unsupported_speed():
    response = client.get("/api/v1/replay/stream?speed=20&limit=1")
    assert response.status_code == 422
