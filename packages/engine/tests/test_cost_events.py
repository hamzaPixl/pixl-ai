"""Tests for CostEventDB aggregation methods."""

from __future__ import annotations

from pathlib import Path

import pytest
from pixl.storage.db.connection import PixlDB


@pytest.fixture()
def db(tmp_path: Path) -> PixlDB:
    """Create a fresh in-memory PixlDB with schema initialized."""
    pixl_dir = tmp_path / ".pixl"
    pixl_dir.mkdir()
    db = PixlDB(tmp_path, pixl_dir=pixl_dir)
    db.initialize()
    return db


def _create_sessions(db: PixlDB) -> None:
    """Create the parent rows required by FK constraints."""
    conn = db.conn
    conn.execute(
        "INSERT INTO workflow_sessions (id, snapshot_hash) VALUES (?, ?)",
        ("session-1", "abc123"),
    )
    conn.execute(
        "INSERT INTO workflow_sessions (id, snapshot_hash) VALUES (?, ?)",
        ("session-2", "def456"),
    )
    conn.commit()


def _seed_events(db: PixlDB) -> None:
    """Insert test cost events across two sessions and three models."""
    _create_sessions(db)
    events = [
        # session-1, gpt-4
        ("session-1", "openai", "gpt-4", 1000, 200, 0.05),
        ("session-1", "openai", "gpt-4", 2000, 400, 0.10),
        # session-1, claude-3
        ("session-1", "anthropic", "claude-3", 500, 100, 0.02),
        # session-2, gpt-4
        ("session-2", "openai", "gpt-4", 3000, 600, 0.15),
        # session-2, gemini-pro
        ("session-2", "google", "gemini-pro", 800, 150, 0.03),
    ]
    for sid, adapter, model, inp, out, cost in events:
        db.cost_events.record(
            sid,
            adapter_name=adapter,
            model_name=model,
            input_tokens=inp,
            output_tokens=out,
            cost_usd=cost,
        )


class TestBreakdownByModel:
    def test_returns_all_models_ungrouped(self, db: PixlDB) -> None:
        _seed_events(db)
        rows = db.cost_events.breakdown_by_model()
        models = [r["model_name"] for r in rows]
        assert set(models) == {"gpt-4", "claude-3", "gemini-pro"}

    def test_ordered_by_cost_desc(self, db: PixlDB) -> None:
        _seed_events(db)
        rows = db.cost_events.breakdown_by_model()
        costs = [r["cost_usd"] for r in rows]
        assert costs == sorted(costs, reverse=True)

    def test_aggregates_tokens_correctly(self, db: PixlDB) -> None:
        _seed_events(db)
        rows = db.cost_events.breakdown_by_model()
        gpt4 = next(r for r in rows if r["model_name"] == "gpt-4")
        # 3 gpt-4 events: 1000+2000+3000=6000 input, 200+400+600=1200 output
        assert gpt4["event_count"] == 3
        assert gpt4["input_tokens"] == 6000
        assert gpt4["output_tokens"] == 1200
        assert abs(gpt4["cost_usd"] - 0.30) < 1e-9

    def test_filter_by_session(self, db: PixlDB) -> None:
        _seed_events(db)
        rows = db.cost_events.breakdown_by_model(session_id="session-1")
        models = {r["model_name"] for r in rows}
        assert models == {"gpt-4", "claude-3"}
        # gemini-pro is only in session-2
        assert "gemini-pro" not in models

    def test_empty_table_returns_empty_list(self, db: PixlDB) -> None:
        rows = db.cost_events.breakdown_by_model()
        assert rows == []


class TestTotalBySession:
    def test_returns_all_sessions(self, db: PixlDB) -> None:
        _seed_events(db)
        rows = db.cost_events.total_by_session()
        session_ids = [r["session_id"] for r in rows]
        assert set(session_ids) == {"session-1", "session-2"}

    def test_ordered_by_cost_desc(self, db: PixlDB) -> None:
        _seed_events(db)
        rows = db.cost_events.total_by_session()
        costs = [r["cost_usd"] for r in rows]
        assert costs == sorted(costs, reverse=True)

    def test_aggregates_correctly(self, db: PixlDB) -> None:
        _seed_events(db)
        rows = db.cost_events.total_by_session()
        s1 = next(r for r in rows if r["session_id"] == "session-1")
        # session-1 has 3 events: 0.05+0.10+0.02 = 0.17
        assert s1["event_count"] == 3
        assert abs(s1["cost_usd"] - 0.17) < 1e-9

    def test_respects_limit(self, db: PixlDB) -> None:
        _seed_events(db)
        rows = db.cost_events.total_by_session(limit=1)
        assert len(rows) == 1

    def test_empty_table_returns_empty_list(self, db: PixlDB) -> None:
        rows = db.cost_events.total_by_session()
        assert rows == []


class TestSummary:
    def test_returns_all_fields(self, db: PixlDB) -> None:
        _seed_events(db)
        s = db.cost_events.summary()
        assert "total_cost_usd" in s
        assert "total_queries" in s
        assert "total_input_tokens" in s
        assert "total_output_tokens" in s
        assert "top_model" in s

    def test_aggregates_correctly(self, db: PixlDB) -> None:
        _seed_events(db)
        s = db.cost_events.summary()
        assert s["total_queries"] == 5
        assert s["total_input_tokens"] == 7300  # 1000+2000+500+3000+800
        assert s["total_output_tokens"] == 1450  # 200+400+100+600+150
        assert abs(s["total_cost_usd"] - 0.35) < 1e-9

    def test_top_model_is_highest_cost(self, db: PixlDB) -> None:
        _seed_events(db)
        s = db.cost_events.summary()
        # gpt-4 has highest total cost (0.30)
        assert s["top_model"] == "gpt-4"

    def test_empty_table_returns_zeroes(self, db: PixlDB) -> None:
        s = db.cost_events.summary()
        assert s["total_cost_usd"] == 0.0
        assert s["total_queries"] == 0
        assert s["total_input_tokens"] == 0
        assert s["total_output_tokens"] == 0
        assert s["top_model"] is None
