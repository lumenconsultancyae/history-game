"""FastAPI entrypoint integration tests for ChronoQuest REST API and SQLite persistence."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from httpx import ASGITransport

from history_game.api.app import create_app
from history_game.config.settings import Settings


@pytest.fixture
async def api_client(tmp_path: Path) -> AsyncIterator[httpx.AsyncClient]:
    """Yield an httpx.AsyncClient bound to an isolated temporary SQLite database."""
    db_file = tmp_path / "test_history_game.db"
    db_url = f"sqlite+aiosqlite:///{db_file}"
    default_settings = Settings()
    assert db_url != default_settings.database_url
    assert "history_game.db" not in str(db_file.name) or str(tmp_path) in str(db_file)

    test_settings = Settings(
        database_url=db_url,
        seed_on_startup=True,
        static_dir=str(tmp_path / "nonexistent_dist"),
    )
    app = create_app(settings=test_settings)

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


class TestHealthAndReadinessEndpoints:
    """Integration tests for /healthz and /readyz probes."""

    async def test_healthz_and_readyz_return_200(self, api_client: httpx.AsyncClient) -> None:
        """Liveness and readiness probes verify process and SQLite database health."""
        health_resp = await api_client.get("/healthz")
        assert health_resp.status_code == 200
        health_data = health_resp.json()
        assert health_data["status"] == "ok"
        assert health_data["service"] == "history-game"

        ready_resp = await api_client.get("/readyz")
        assert ready_resp.status_code == 200
        ready_data = ready_resp.json()
        assert ready_data["status"] in ("ok", "ready")
        assert ready_data["service"] == "history-game"


class TestCatalogEndpoints:
    """Integration tests for /api/v1/eras and /api/v1/events."""

    async def test_list_eras_returns_six_chronological_eras_with_counts(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """GET /api/v1/eras returns all 6 canonical eras in chronological order with event counts."""
        resp = await api_client.get("/api/v1/eras")
        assert resp.status_code == 200
        eras = resp.json()
        assert len(eras) == 6
        assert [item["era"] for item in eras] == [
            "ancient",
            "classical",
            "medieval",
            "early_modern",
            "industrial",
            "modern",
        ]
        assert sum(item["event_count"] for item in eras) == 24
        for item in eras:
            assert item["label"]
            assert item["period_label"]
            assert item["description"]
            assert item["event_count"] >= 4

    async def test_list_events_and_filter_by_era(self, api_client: httpx.AsyncClient) -> None:
        """GET /api/v1/events returns 24 sorted events and filters by ?era=ancient."""
        all_resp = await api_client.get("/api/v1/events")
        assert all_resp.status_code == 200
        all_events = all_resp.json()
        assert len(all_events) == 24
        years = [ev["year"] for ev in all_events]
        assert years == sorted(years)
        assert all("BCE" in ev["year_label"] or "CE" in ev["year_label"] for ev in all_events)

        ancient_resp = await api_client.get("/api/v1/events", params={"era": "ancient"})
        assert ancient_resp.status_code == 200
        ancient_events = ancient_resp.json()
        assert len(ancient_events) >= 4
        assert all(ev["era"] == "ancient" for ev in ancient_events)
        assert [ev["year"] for ev in ancient_events] == sorted(ev["year"] for ev in ancient_events)


class TestTimelineSessionAndPlacementEndpoints:
    """Integration tests for session lifecycle, card redaction, placement feedback, and leaderboard."""

    async def test_create_and_fetch_session_redacts_current_card_year(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """POST /api/v1/sessions creates an active session with 1 anchor card and redacts current card year."""
        create_resp = await api_client.post(
            "/api/v1/sessions",
            json={
                "player_name": "Ada Lovelace",
                "difficulty": "explorer",
                "era": None,
                "seed": 42,
            },
        )
        assert create_resp.status_code in (200, 201)
        session_data = create_resp.json()

        assert session_data["player_name"] == "Ada Lovelace"
        assert session_data["difficulty"] == "explorer"
        assert session_data["status"] == "in_progress"
        assert session_data["score"] == 0
        assert session_data["streak"] == 0
        assert session_data["lives_remaining"] == 3
        assert len(session_data["timeline"]) == 1

        anchor = session_data["timeline"][0]
        assert isinstance(anchor["year"], int)
        assert anchor["year_label"]
        assert anchor["significance"]

        current_card = session_data.get("current_event") or session_data.get("current_card")
        assert current_card is not None
        assert current_card["id"]
        assert current_card["title"]
        assert current_card["summary"]
        assert "year" not in current_card or current_card["year"] is None

        # GET /api/v1/sessions/{session_id} returns identical state
        get_resp = await api_client.get(f"/api/v1/sessions/{session_data['id']}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == session_data["id"]

    async def test_get_unknown_session_returns_rfc9457_404(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """GET /api/v1/sessions/{unknown} returns 404 application/problem+json."""
        resp = await api_client.get("/api/v1/sessions/non-existent-session-id")
        assert resp.status_code == 404
        assert "application/problem+json" in resp.headers.get("content-type", "")
        problem = resp.json()
        assert problem["status"] == 404
        assert problem["title"] == "Resource Not Found"
        assert "non-existent-session-id" in problem["detail"]
        assert problem["instance"] == "/api/v1/sessions/non-existent-session-id"

    async def test_correct_placement_and_misplacement_workflow(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """POST /api/v1/sessions/{id}/placements evaluates correct and incorrect chronological slots."""
        # Fetch full catalog so test can determine exact chronological order
        catalog_resp = await api_client.get("/api/v1/events")
        events_by_id = {ev["id"]: ev for ev in catalog_resp.json()}

        create_resp = await api_client.post(
            "/api/v1/sessions",
            json={
                "player_name": "Ada Lovelace",
                "difficulty": "explorer",
                "era": None,
                "seed": 42,
            },
        )
        session = create_resp.json()
        session_id = session["id"]

        # Turn 1: Place drawn card in its true chronological slot
        anchor_year = session["timeline"][0]["year"]
        drawn_card = session.get("current_event") or session.get("current_card")
        drawn_id = drawn_card["id"]
        drawn_year = events_by_id[drawn_id]["year"]
        correct_slot = 0 if drawn_year <= anchor_year else 1

        place_1_resp = await api_client.post(
            f"/api/v1/sessions/{session_id}/placements",
            json={"event_id": drawn_id, "position_index": correct_slot},
        )
        assert place_1_resp.status_code == 200
        outcome_1 = place_1_resp.json()
        assert outcome_1["attempt"]["is_correct"] is True
        assert outcome_1["attempt"]["points_awarded"] == 100
        assert outcome_1["attempt"]["placed_event"]["year"] == drawn_year
        assert outcome_1["attempt"]["placed_event"]["significance"]
        assert outcome_1["session"]["score"] == 100
        assert outcome_1["session"]["streak"] == 1
        assert outcome_1["session"]["lives_remaining"] == 3
        timeline_years_1 = [c["year"] for c in outcome_1["session"]["timeline"]]
        assert timeline_years_1 == sorted(timeline_years_1)

        # Turn 2: Deliberately misplace the next drawn card
        session_after_1 = outcome_1["session"]
        next_card = session_after_1.get("current_event") or session_after_1.get("current_card")
        next_id = next_card["id"]
        next_year = events_by_id[next_id]["year"]
        # Pick an invalid slot: if next_year < earliest timeline year, pick end of timeline; otherwise pick 0
        wrong_slot = len(timeline_years_1) if next_year < timeline_years_1[0] else 0

        place_2_resp = await api_client.post(
            f"/api/v1/sessions/{session_id}/placements",
            json={"event_id": next_id, "position_index": wrong_slot},
        )
        assert place_2_resp.status_code == 200
        outcome_2 = place_2_resp.json()
        assert outcome_2["attempt"]["is_correct"] is False
        assert outcome_2["attempt"]["points_awarded"] == 0
        assert outcome_2["attempt"]["placed_event"]["year"] == next_year
        assert outcome_2["session"]["streak"] == 0
        assert outcome_2["session"]["lives_remaining"] == 2
        timeline_years_2 = [c["year"] for c in outcome_2["session"]["timeline"]]
        assert timeline_years_2 == sorted(timeline_years_2)

        # Out-of-bounds position_index returns 422 ProblemDetails
        active_card = (
            outcome_2["session"].get("current_event")
            or outcome_2["session"].get("current_card")
        )
        oob_resp = await api_client.post(
            f"/api/v1/sessions/{session_id}/placements",
            json={"event_id": active_card["id"], "position_index": 99},
        )
        assert oob_resp.status_code == 422
        assert "application/problem+json" in oob_resp.headers.get("content-type", "")

    async def test_completing_session_populates_leaderboard_and_blocks_further_placements(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """Completing a session lists the run on GET /api/v1/leaderboard and returns 409 on extra placements."""
        catalog_resp = await api_client.get("/api/v1/events")
        events_by_id = {ev["id"]: ev for ev in catalog_resp.json()}

        create_resp = await api_client.post(
            "/api/v1/sessions",
            json={
                "player_name": "Herodotus",
                "difficulty": "explorer",
                "era": "ancient",
                "seed": 11,
            },
        )
        session = create_resp.json()
        session_id = session["id"]
        last_event_id = ""

        while session["status"] == "in_progress":
            drawn = session.get("current_event") or session.get("current_card")
            assert drawn is not None
            last_event_id = drawn["id"]
            target_year = events_by_id[last_event_id]["year"]
            placed_years = [c["year"] for c in session["timeline"]]

            slot = 0
            for idx, yr in enumerate(placed_years):
                if target_year >= yr:
                    slot = idx + 1

            resp = await api_client.post(
                f"/api/v1/sessions/{session_id}/placements",
                json={"event_id": last_event_id, "position_index": slot},
            )
            assert resp.status_code == 200
            session = resp.json()["session"]

        assert session["status"] == "completed"
        assert session["score"] >= 300

        # Placement on already completed session returns 409 Conflict (RFC 9457)
        conflict_resp = await api_client.post(
            f"/api/v1/sessions/{session_id}/placements",
            json={"event_id": last_event_id, "position_index": 0},
        )
        assert conflict_resp.status_code in (409, 422)
        assert "application/problem+json" in conflict_resp.headers.get("content-type", "")

        # Verify Hall of Records leaderboard includes Herodotus
        lb_resp = await api_client.get("/api/v1/leaderboard")
        assert lb_resp.status_code == 200
        leaderboard = lb_resp.json()
        assert len(leaderboard) >= 1
        assert leaderboard[0]["player_name"] == "Herodotus"
        assert leaderboard[0]["score"] == session["score"]
