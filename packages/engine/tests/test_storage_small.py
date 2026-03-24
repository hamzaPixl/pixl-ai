"""Tests for 11 small storage DB modules.

Each test class isolates a single store and uses a fresh PixlDB backed by a
tmp-dir SQLite database (the standard in-project pattern).

Prerequisite helpers insert the parent records required by FK constraints
(workflow_sessions rows) before inserting child records.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from pixl.models.metrics import AgentMetrics
from pixl.storage.db.connection import PixlDB


# ---------------------------------------------------------------------------
# Shared fixture + helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def db(tmp_path: Path) -> PixlDB:
    """Fresh PixlDB for each test, fully initialized with the current schema."""
    pixl_dir = tmp_path / ".pixl"
    pixl_dir.mkdir()
    pixl_db = PixlDB(tmp_path, pixl_dir=pixl_dir)
    pixl_db.initialize()
    return pixl_db


def _seed_session(db: PixlDB, session_id: str = "sess-001") -> str:
    """Insert a minimal workflow_sessions row to satisfy FK constraints."""
    db.conn.execute(
        "INSERT OR IGNORE INTO workflow_sessions (id, snapshot_hash) VALUES (?, ?)",
        (session_id, "hash-" + session_id),
    )
    db.conn.commit()
    return session_id


def _seed_artifact(db: PixlDB, artifact_id: str = "art-001", session_id: str | None = None) -> str:
    """Insert a minimal artifacts row to satisfy FK constraints on artifact_id."""
    db.conn.execute(
        "INSERT OR IGNORE INTO artifacts (id, type, name) VALUES (?, ?, ?)",
        (artifact_id, "document", f"test-artifact-{artifact_id}"),
    )
    db.conn.commit()
    return artifact_id


def _seed_chain(db: PixlDB, chain_id: str = "chain-001") -> str:
    """Insert a minimal execution_chains row.

    execution_chains → epics (NOT NULL FK) → optionally roadmaps (nullable).
    We insert an epic with no roadmap/milestone to keep it simple.
    """
    epic_id = f"epic-for-{chain_id}"
    db.conn.execute(
        "INSERT OR IGNORE INTO epics (id, title, original_prompt) VALUES (?, ?, ?)",
        (epic_id, "Test epic", "prompt"),
    )
    db.conn.execute(
        "INSERT OR IGNORE INTO execution_chains (id, epic_id) VALUES (?, ?)",
        (chain_id, epic_id),
    )
    db.conn.commit()
    return chain_id


# ===========================================================================
# 1. heartbeat_runs.py
# ===========================================================================


class TestHeartbeatRunDB:
    def test_create_run_returns_queued_status(self, db: PixlDB) -> None:
        """should return a queued run dict when creating a new run"""
        _seed_session(db, "sess-hb")
        run = db.heartbeat_runs.create_run("run-001", "sess-hb")
        assert run["status"] == "queued"
        assert run["id"] == "run-001"
        assert run["session_id"] == "sess-hb"

    def test_create_run_with_context_snapshot(self, db: PixlDB) -> None:
        """should persist context_snapshot JSON when provided"""
        _seed_session(db, "sess-hb2")
        snapshot = {"key": "value"}
        db.heartbeat_runs.create_run("run-snap", "sess-hb2", context_snapshot=snapshot)
        run = db.heartbeat_runs.get_run("run-snap")
        assert run is not None
        stored = json.loads(run["context_snapshot"])
        assert stored["key"] == "value"

    def test_get_run_returns_none_for_missing(self, db: PixlDB) -> None:
        """should return None when run ID does not exist"""
        assert db.heartbeat_runs.get_run("nonexistent") is None

    def test_start_run_transitions_status_to_running(self, db: PixlDB) -> None:
        """should transition a queued run to running status"""
        _seed_session(db, "sess-hb3")
        db.heartbeat_runs.create_run("run-002", "sess-hb3")
        db.heartbeat_runs.start_run("run-002")
        run = db.heartbeat_runs.get_run("run-002")
        assert run is not None
        assert run["status"] == "running"
        assert run["started_at"] is not None

    def test_heartbeat_updates_timestamp(self, db: PixlDB) -> None:
        """should update heartbeat_at when heartbeat is called on a running run"""
        _seed_session(db, "sess-hb4")
        db.heartbeat_runs.create_run("run-003", "sess-hb4")
        db.heartbeat_runs.start_run("run-003")
        db.heartbeat_runs.heartbeat("run-003")
        run = db.heartbeat_runs.get_run("run-003")
        assert run is not None
        assert run["heartbeat_at"] is not None

    def test_complete_run_sets_succeeded_status(self, db: PixlDB) -> None:
        """should mark a run as succeeded after completion"""
        _seed_session(db, "sess-hb5")
        db.heartbeat_runs.create_run("run-004", "sess-hb5")
        db.heartbeat_runs.start_run("run-004")
        db.heartbeat_runs.complete_run("run-004", status="succeeded", input_tokens=100, output_tokens=50)
        run = db.heartbeat_runs.get_run("run-004")
        assert run is not None
        assert run["status"] == "succeeded"
        assert run["input_tokens"] == 100
        assert run["output_tokens"] == 50

    def test_fail_run_sets_failed_status(self, db: PixlDB) -> None:
        """should mark a run as failed with an error message"""
        _seed_session(db, "sess-hb6")
        db.heartbeat_runs.create_run("run-005", "sess-hb6")
        db.heartbeat_runs.start_run("run-005")
        db.heartbeat_runs.fail_run("run-005", "something went wrong")
        run = db.heartbeat_runs.get_run("run-005")
        assert run is not None
        assert run["status"] == "failed"
        assert run["error_message"] == "something went wrong"

    def test_list_for_session_returns_all_runs(self, db: PixlDB) -> None:
        """should return all runs for a session ordered by created_at desc"""
        _seed_session(db, "sess-hb7")
        db.heartbeat_runs.create_run("run-a", "sess-hb7")
        db.heartbeat_runs.create_run("run-b", "sess-hb7")
        runs = db.heartbeat_runs.list_for_session("sess-hb7")
        assert len(runs) == 2

    def test_list_for_session_returns_empty_for_unknown_session(self, db: PixlDB) -> None:
        """should return empty list for session with no runs"""
        runs = db.heartbeat_runs.list_for_session("no-such-session")
        assert runs == []

    def test_get_active_run_returns_running_run(self, db: PixlDB) -> None:
        """should return the running run for a session"""
        _seed_session(db, "sess-hb8")
        db.heartbeat_runs.create_run("run-active", "sess-hb8")
        db.heartbeat_runs.start_run("run-active")
        active = db.heartbeat_runs.get_active_run("sess-hb8")
        assert active is not None
        assert active["id"] == "run-active"

    def test_get_active_run_returns_none_when_no_running_run(self, db: PixlDB) -> None:
        """should return None when no running run exists for a session"""
        _seed_session(db, "sess-hb9")
        db.heartbeat_runs.create_run("run-q", "sess-hb9")
        # still queued, not started
        assert db.heartbeat_runs.get_active_run("sess-hb9") is None

    def test_find_stalled_runs_returns_empty_when_none_stalled(self, db: PixlDB) -> None:
        """should return empty list when no runs are stalled"""
        results = db.heartbeat_runs.find_stalled_runs(threshold_seconds=60)
        assert results == []

    def test_increment_usage_adds_to_counters(self, db: PixlDB) -> None:
        """should atomically add tokens and cost to the run"""
        _seed_session(db, "sess-hb10")
        db.heartbeat_runs.create_run("run-inc", "sess-hb10")
        db.heartbeat_runs.start_run("run-inc")
        db.heartbeat_runs.increment_usage("run-inc", input_tokens=50, output_tokens=25, cost_usd=0.01, steps=1)
        run = db.heartbeat_runs.get_run("run-inc")
        assert run is not None
        assert run["input_tokens"] == 50
        assert run["output_tokens"] == 25


# ===========================================================================
# 2. incidents.py
# ===========================================================================


class TestIncidentDB:
    def _record(self, db: PixlDB, incident_id: str = "inc-001", session_id: str = "sess-inc") -> object:
        _seed_session(db, session_id)
        return db.incidents.record_incident(
            incident_id=incident_id,
            session_id=session_id,
            node_id="node-1",
            feature_id=None,
            error_type="provider_error",
            error_message="timeout connecting to API",
            recovery_action="retry",
            outcome="succeeded",
            attempt_count=2,
            payload_json="{}",
        )

    def test_record_incident_returns_incident_record(self, db: PixlDB) -> None:
        """should return an IncidentRecord with the correct fields"""
        record = self._record(db)
        assert record.id == "inc-001"
        assert record.outcome == "succeeded"
        assert record.error_type == "provider_error"

    def test_get_returns_none_for_missing_id(self, db: PixlDB) -> None:
        """should return None when incident ID does not exist"""
        assert db.incidents.get("missing-id") is None

    def test_get_returns_stored_incident(self, db: PixlDB) -> None:
        """should retrieve an incident by its ID"""
        self._record(db)
        incident = db.incidents.get("inc-001")
        assert incident is not None
        assert incident.error_message == "timeout connecting to API"

    def test_get_by_session_returns_all_incidents_for_session(self, db: PixlDB) -> None:
        """should return all incidents for a given session"""
        self._record(db, "inc-001", "sess-A")
        self._record(db, "inc-002", "sess-A")
        self._record(db, "inc-003", "sess-B")
        results = db.incidents.get_by_session("sess-A")
        assert len(results) == 2
        assert all(r.session_id == "sess-A" for r in results)

    def test_get_by_feature_returns_incidents_for_feature(self, db: PixlDB) -> None:
        """should return incidents filtered by feature_id"""
        _seed_session(db, "sess-f")
        db.incidents.record_incident(
            incident_id="inc-feat",
            session_id="sess-f",
            node_id=None,
            feature_id="feat-1",
            error_type="contract_error",
            error_message="schema mismatch",
            recovery_action=None,
            outcome="failed",
            attempt_count=1,
            payload_json="{}",
        )
        results = db.incidents.get_by_feature("feat-1")
        assert len(results) == 1
        assert results[0].feature_id == "feat-1"

    def test_list_recent_returns_incidents_ordered_desc(self, db: PixlDB) -> None:
        """should return incidents ordered by created_at descending"""
        self._record(db, "inc-r1", "sess-r1")
        self._record(db, "inc-r2", "sess-r2")
        incidents = db.incidents.list_recent(limit=10)
        assert len(incidents) >= 2

    def test_find_by_error_type_filters_correctly(self, db: PixlDB) -> None:
        """should return only incidents with matching error type"""
        _seed_session(db, "sess-et")
        self._record(db, "inc-et1", "sess-et")
        db.incidents.record_incident(
            incident_id="inc-et2",
            session_id="sess-et",
            node_id=None,
            feature_id=None,
            error_type="contract_error",
            error_message="other error",
            recovery_action=None,
            outcome="failed",
            attempt_count=1,
            payload_json="{}",
        )
        results = db.incidents.find_by_error_type("provider_error")
        assert all(r.error_type == "provider_error" for r in results)

    def test_find_by_error_type_with_outcome_filter(self, db: PixlDB) -> None:
        """should further filter by outcome when provided"""
        self._record(db, "inc-oc1", "sess-oc")
        results = db.incidents.find_by_error_type("provider_error", outcome="succeeded")
        assert all(r.outcome == "succeeded" for r in results)

    def test_get_stats_returns_expected_keys(self, db: PixlDB) -> None:
        """should return a dict with total, success_rate, and outcome breakdown"""
        self._record(db)
        stats = db.incidents.get_stats(days=30)
        assert "total" in stats
        assert "success_rate" in stats
        assert "by_outcome" in stats

    def test_get_success_rate_returns_float(self, db: PixlDB) -> None:
        """should return a float between 0.0 and 1.0"""
        self._record(db)
        rate = db.incidents.get_success_rate("provider_error", days=30)
        assert 0.0 <= rate <= 1.0

    def test_to_dict_includes_payload_key(self, db: PixlDB) -> None:
        """should include 'payload' key in to_dict() output"""
        record = self._record(db)
        d = record.to_dict()
        assert "payload" in d

    def test_find_similar_fts_returns_empty_for_blank_query(self, db: PixlDB) -> None:
        """should return empty list when query is blank"""
        self._record(db)
        results = db.incidents.find_similar_fts("provider_error", "   ")
        assert results == []


# ===========================================================================
# 3. knowledge.py
# ===========================================================================


class TestKnowledgeDB:
    def test_upsert_document_returns_id(self, db: PixlDB) -> None:
        """should return a document ID when upserting a new document"""
        doc_id = db.knowledge.upsert_document("src/main.py", "abc123")
        assert isinstance(doc_id, int)
        assert doc_id > 0

    def test_upsert_document_returns_same_id_for_same_hash(self, db: PixlDB) -> None:
        """should return the same ID when upserting with the same path and hash"""
        id1 = db.knowledge.upsert_document("src/main.py", "abc123")
        id2 = db.knowledge.upsert_document("src/main.py", "abc123")
        assert id1 == id2

    def test_upsert_document_updates_hash_on_change(self, db: PixlDB) -> None:
        """should update the hash when content changes"""
        id1 = db.knowledge.upsert_document("src/main.py", "abc123")
        id2 = db.knowledge.upsert_document("src/main.py", "xyz789")
        # same ID, but hash is now different
        assert id1 == id2
        doc = db.knowledge.get_document("src/main.py")
        assert doc is not None
        assert doc["content_hash"] == "xyz789"

    def test_get_document_returns_none_for_missing(self, db: PixlDB) -> None:
        """should return None when document path does not exist"""
        assert db.knowledge.get_document("missing.py") is None

    def test_get_document_returns_stored_document(self, db: PixlDB) -> None:
        """should retrieve a document by its path"""
        db.knowledge.upsert_document("src/main.py", "abc123")
        doc = db.knowledge.get_document("src/main.py")
        assert doc is not None
        assert doc["path"] == "src/main.py"

    def test_add_chunk_stores_chunk(self, db: PixlDB) -> None:
        """should persist a chunk associated with a document"""
        doc_id = db.knowledge.upsert_document("src/mod.py", "hash1")
        db.knowledge.add_chunk(
            chunk_id="chunk-001",
            document_id=doc_id,
            title="My Function",
            content="def my_func(): pass",
            source="src/mod.py",
            chunk_type="concept",
            keywords=["func", "python"],
        )
        db.knowledge._conn.commit()
        chunks = db.knowledge.list_chunks()
        assert any(c["id"] == "chunk-001" for c in chunks)

    def test_remove_chunks_for_document_returns_count(self, db: PixlDB) -> None:
        """should remove all chunks for a document and return the count"""
        doc_id = db.knowledge.upsert_document("src/mod.py", "hash1")
        db.knowledge.add_chunk(
            chunk_id="chunk-del",
            document_id=doc_id,
            title="T",
            content="C",
            source="src/mod.py",
        )
        db.knowledge._conn.commit()
        removed = db.knowledge.remove_chunks_for_document(doc_id)
        assert removed == 1

    def test_add_chunks_batch_inserts_multiple(self, db: PixlDB) -> None:
        """should bulk-insert chunks and return the count"""
        doc_id = db.knowledge.upsert_document("src/batch.py", "batchhash")
        chunks = [
            {"id": "bc-1", "title": "T1", "content": "C1", "source": "src/batch.py"},
            {"id": "bc-2", "title": "T2", "content": "C2", "source": "src/batch.py"},
        ]
        count = db.knowledge.add_chunks_batch(chunks, doc_id)
        assert count == 2

    def test_list_chunks_returns_all_chunks(self, db: PixlDB) -> None:
        """should return all stored chunks"""
        doc_id = db.knowledge.upsert_document("src/l.py", "lhash")
        db.knowledge.add_chunk("lc-1", doc_id, "T", "C", "src/l.py")
        db.knowledge._conn.commit()
        chunks = db.knowledge.list_chunks()
        assert len(chunks) >= 1

    def test_search_returns_empty_for_blank_query(self, db: PixlDB) -> None:
        """should return empty list when query is blank"""
        results = db.knowledge.search("   ")
        assert results == []

    def test_search_returns_results_for_matching_term(self, db: PixlDB) -> None:
        """should return chunks that match the search query"""
        doc_id = db.knowledge.upsert_document("src/search.py", "sh")
        db.knowledge.add_chunk("sc-1", doc_id, "Authentication", "JWT token auth flow", "src/search.py")
        db.knowledge._conn.commit()
        results = db.knowledge.search("authentication")
        assert len(results) >= 1

    def test_update_manifest_and_get_manifest(self, db: PixlDB) -> None:
        """should store and retrieve the build manifest"""
        db.knowledge.update_manifest(chunk_count=10, source_count=3, build_duration_ms=500)
        manifest = db.knowledge.get_manifest()
        assert manifest is not None
        assert manifest["chunk_count"] == 10

    def test_get_status_returns_counts(self, db: PixlDB) -> None:
        """should return document and chunk counts in status"""
        status = db.knowledge.get_status()
        assert "documents" in status
        assert "chunks" in status

    def test_clear_removes_all_data(self, db: PixlDB) -> None:
        """should remove all chunks, documents, and manifest on clear"""
        doc_id = db.knowledge.upsert_document("src/clr.py", "clrhash")
        db.knowledge.add_chunk("clr-1", doc_id, "T", "C", "src/clr.py")
        db.knowledge._conn.commit()
        db.knowledge.clear()
        assert db.knowledge.list_chunks() == []
        assert db.knowledge.get_document("src/clr.py") is None

    def test_get_changed_documents_returns_new_paths(self, db: PixlDB) -> None:
        """should include paths not yet indexed as changed"""
        changed = db.knowledge.get_changed_documents({"new_file.py": "newhash"})
        assert "new_file.py" in changed

    def test_remove_stale_documents_removes_missing_paths(self, db: PixlDB) -> None:
        """should remove documents whose paths are no longer in the current set"""
        db.knowledge.upsert_document("stale.py", "sh")
        db.knowledge._conn.commit()
        removed = db.knowledge.remove_stale_documents(current_paths=set())
        assert removed == 1


# ===========================================================================
# 4. metrics.py
# ===========================================================================


class TestMetricsStore:
    def _make_metrics(self, session_id: str = "sess-met", node_id: str = "node-1") -> AgentMetrics:
        return AgentMetrics(
            agent_name="qa-engineer",
            model_name="claude-sonnet",
            session_id=session_id,
            node_id=node_id,
            started_at=datetime(2024, 1, 1, 12, 0, 0),
            completed_at=datetime(2024, 1, 1, 12, 0, 30),
            input_tokens=500,
            output_tokens=200,
            total_tokens=700,
            total_cost_usd=0.01,
            success=True,
        )

    def test_store_agent_metrics_returns_string_id(self, db: PixlDB) -> None:
        """should return a string row ID after storing metrics"""
        _seed_session(db, "sess-met")
        result = db.metrics.store_agent_metrics(self._make_metrics())
        assert isinstance(result, str)
        assert result.isdigit()

    def test_get_agent_performance_returns_expected_keys(self, db: PixlDB) -> None:
        """should return performance dict with required keys"""
        _seed_session(db, "sess-met")
        db.metrics.store_agent_metrics(self._make_metrics())
        perf = db.metrics.get_agent_performance("qa-engineer")
        assert "total_executions" in perf
        assert "success_rate" in perf
        assert "avg_cost_usd" in perf

    def test_get_agent_performance_counts_executions(self, db: PixlDB) -> None:
        """should count agent executions correctly"""
        _seed_session(db, "sess-met")
        db.metrics.store_agent_metrics(self._make_metrics())
        db.metrics.store_agent_metrics(self._make_metrics())
        perf = db.metrics.get_agent_performance("qa-engineer")
        assert perf["total_executions"] == 2

    def test_get_session_metrics_returns_list(self, db: PixlDB) -> None:
        """should return all AgentMetrics for a session"""
        _seed_session(db, "sess-list")
        db.metrics.store_agent_metrics(self._make_metrics("sess-list"))
        results = db.metrics.get_session_metrics("sess-list")
        assert len(results) == 1
        assert results[0].session_id == "sess-list"

    def test_get_session_metrics_returns_empty_for_unknown_session(self, db: PixlDB) -> None:
        """should return empty list when no metrics exist for session"""
        assert db.metrics.get_session_metrics("no-such-session") == []

    def test_get_feature_metrics_returns_for_feature(self, db: PixlDB) -> None:
        """should return metrics filtered by feature_id"""
        _seed_session(db, "sess-feat")
        # features(id) is required when feature_id is not NULL on agent_metrics
        db.conn.execute(
            "INSERT OR IGNORE INTO features (id, title) VALUES (?, ?)",
            ("feat-99", "Feature 99"),
        )
        db.conn.commit()
        metrics = AgentMetrics(
            agent_name="backend-engineer",
            model_name="claude-sonnet",
            session_id="sess-feat",
            node_id="node-feat",
            feature_id="feat-99",
            started_at=datetime(2024, 1, 1),
        )
        db.metrics.store_agent_metrics(metrics)
        results = db.metrics.get_feature_metrics("feat-99")
        assert len(results) == 1
        assert results[0].feature_id == "feat-99"

    def test_get_agent_performance_with_timeframe_hours(self, db: PixlDB) -> None:
        """should filter by timeframe_hours without error"""
        _seed_session(db, "sess-met")
        db.metrics.store_agent_metrics(self._make_metrics())
        # Wide timeframe should include the record
        perf = db.metrics.get_agent_performance("qa-engineer", timeframe_hours=24 * 365 * 10)
        assert isinstance(perf, dict)


# ===========================================================================
# 5. quality_scores.py
# ===========================================================================


class TestQualityScoreDB:
    def test_record_returns_row_id(self, db: PixlDB) -> None:
        """should return a positive integer row ID after recording a score"""
        row_id = db.quality_scores.record("chain", "chain-001", "accuracy", 0.95)
        assert isinstance(row_id, int)
        assert row_id > 0

    def test_record_raises_for_invalid_scope_type(self, db: PixlDB) -> None:
        """should raise ValueError for unsupported scope_type"""
        with pytest.raises(ValueError, match="invalid scope_type"):
            db.quality_scores.record("invalid_scope", "x", "metric", 0.5)

    def test_get_scores_returns_recorded_scores(self, db: PixlDB) -> None:
        """should return the recorded scores for the given scope"""
        db.quality_scores.record("session", "sess-qs", "f1", 0.88)
        scores = db.quality_scores.get_scores("session", "sess-qs")
        assert len(scores) == 1
        assert scores[0]["value"] == pytest.approx(0.88)

    def test_get_scores_filtered_by_metric(self, db: PixlDB) -> None:
        """should return only scores matching the requested metric"""
        db.quality_scores.record("session", "sess-filt", "f1", 0.88)
        db.quality_scores.record("session", "sess-filt", "precision", 0.90)
        scores = db.quality_scores.get_scores("session", "sess-filt", metric="f1")
        assert all(s["metric"] == "f1" for s in scores)

    def test_get_scores_returns_empty_for_unknown_scope(self, db: PixlDB) -> None:
        """should return empty list when no scores exist for the scope"""
        scores = db.quality_scores.get_scores("node", "no-such-node")
        assert scores == []

    def test_get_trends_returns_oldest_first(self, db: PixlDB) -> None:
        """should return trends ordered oldest first"""
        db.quality_scores.record("chain", "c1", "accuracy", 0.80)
        db.quality_scores.record("chain", "c1", "accuracy", 0.85)
        trends = db.quality_scores.get_trends("chain", "c1", "accuracy")
        assert len(trends) == 2
        # Values should be in ascending time order (oldest first)
        assert trends[0]["value"] == pytest.approx(0.80)
        assert trends[1]["value"] == pytest.approx(0.85)

    def test_get_latest_scores_returns_most_recent_per_metric(self, db: PixlDB) -> None:
        """should return the most recent value for each metric"""
        db.quality_scores.record("feature", "feat-q", "accuracy", 0.70)
        db.quality_scores.record("feature", "feat-q", "accuracy", 0.90)
        latest = db.quality_scores.get_latest_scores("feature", "feat-q")
        assert "accuracy" in latest
        assert latest["accuracy"] == pytest.approx(0.90)

    def test_all_valid_scope_types_accepted(self, db: PixlDB) -> None:
        """should accept all valid scope types without raising"""
        for scope in ("chain", "node", "session", "feature", "epic"):
            row_id = db.quality_scores.record(scope, f"{scope}-id", "test_metric", 1.0)
            assert row_id > 0


# ===========================================================================
# 6. session_reports.py
# ===========================================================================


class TestSessionReportDB:
    def test_enqueue_returns_job_dict_with_id(self, db: PixlDB) -> None:
        """should return a job dict with an ID and queued status"""
        _seed_session(db, "sess-rpt")
        job = db.session_reports.enqueue_session_report_job("sess-rpt")
        assert "id" in job
        assert job["status"] == "queued"
        assert job["session_id"] == "sess-rpt"

    def test_get_session_report_job_returns_job(self, db: PixlDB) -> None:
        """should retrieve a job by ID"""
        _seed_session(db, "sess-rpt2")
        job = db.session_reports.enqueue_session_report_job("sess-rpt2")
        fetched = db.session_reports.get_session_report_job(job["id"])
        assert fetched is not None
        assert fetched["id"] == job["id"]

    def test_get_session_report_job_returns_none_for_missing(self, db: PixlDB) -> None:
        """should return None when job ID does not exist"""
        result = db.session_reports.get_session_report_job("no-such-job")
        assert result is None

    def test_claim_next_returns_oldest_queued_job(self, db: PixlDB) -> None:
        """should claim the oldest queued job and mark it running"""
        _seed_session(db, "sess-rpt3")
        db.session_reports.enqueue_session_report_job("sess-rpt3", trigger="manual_draft")
        db.session_reports.enqueue_session_report_job("sess-rpt3", trigger="auto_terminal")
        claimed = db.session_reports.claim_next_session_report_job()
        assert claimed is not None
        assert claimed["status"] == "running"

    def test_claim_next_returns_none_when_queue_empty(self, db: PixlDB) -> None:
        """should return None when no jobs are queued"""
        assert db.session_reports.claim_next_session_report_job() is None

    def test_complete_job_sets_completed_status(self, db: PixlDB) -> None:
        """should mark a running job as completed with an artifact_id"""
        _seed_session(db, "sess-rpt4")
        _seed_artifact(db, "art-rpt4")
        job = db.session_reports.enqueue_session_report_job("sess-rpt4")
        db.session_reports.claim_next_session_report_job()
        success = db.session_reports.complete_session_report_job(job["id"], "art-rpt4")
        assert success is True
        fetched = db.session_reports.get_session_report_job(job["id"])
        assert fetched is not None
        assert fetched["status"] == "completed"

    def test_fail_job_sets_failed_status(self, db: PixlDB) -> None:
        """should mark a running job as failed with an error message"""
        _seed_session(db, "sess-rpt5")
        job = db.session_reports.enqueue_session_report_job("sess-rpt5")
        db.session_reports.claim_next_session_report_job()
        success = db.session_reports.fail_session_report_job(job["id"], "DB error")
        assert success is True

    def test_list_session_report_jobs_filters_by_session(self, db: PixlDB) -> None:
        """should return only jobs for the specified session"""
        _seed_session(db, "sess-list-rpt")
        _seed_session(db, "sess-other-rpt")
        db.session_reports.enqueue_session_report_job("sess-list-rpt")
        db.session_reports.enqueue_session_report_job("sess-other-rpt")
        jobs = db.session_reports.list_session_report_jobs(session_id="sess-list-rpt")
        assert all(j["session_id"] == "sess-list-rpt" for j in jobs)

    def test_enqueue_or_get_inflight_returns_existing_when_queued(self, db: PixlDB) -> None:
        """should return existing inflight job instead of creating a new one"""
        _seed_session(db, "sess-ifl")
        job1 = db.session_reports.enqueue_session_report_job("sess-ifl", trigger="manual_draft")
        job2 = db.session_reports.enqueue_or_get_inflight_session_report_job(
            "sess-ifl", trigger="manual_draft"
        )
        assert job1["id"] == job2["id"]

    def test_requeue_job_increments_retry_count(self, db: PixlDB) -> None:
        """should requeue a job and increment its retry_count"""
        _seed_session(db, "sess-requeue")
        job = db.session_reports.enqueue_session_report_job("sess-requeue")
        success = db.session_reports.requeue_session_report_job(job["id"])
        assert success is True


# ===========================================================================
# 7. summaries.py
# ===========================================================================


class TestSummaryDB:
    def test_upsert_summary_returns_id_string(self, db: PixlDB) -> None:
        """should return a string ID when upserting a summary"""
        record_id = db.summaries.upsert_summary("plan.md", "hash001", "Summary text")
        assert isinstance(record_id, str)
        assert record_id.startswith("sum-")

    def test_get_summary_returns_none_for_missing(self, db: PixlDB) -> None:
        """should return None when no summary exists for the given name/hash"""
        assert db.summaries.get_summary("plan.md", "missing-hash") is None

    def test_get_summary_returns_stored_record(self, db: PixlDB) -> None:
        """should retrieve a stored summary by artifact_name and source_hash"""
        db.summaries.upsert_summary("plan.md", "hash001", "Summary text", method="heuristic")
        record = db.summaries.get_summary("plan.md", "hash001")
        assert record is not None
        assert record.summary_text == "Summary text"
        assert record.method == "heuristic"

    def test_upsert_updates_existing_summary(self, db: PixlDB) -> None:
        """should update summary_text when the same name/hash is upserted again"""
        db.summaries.upsert_summary("plan.md", "hash001", "Old text")
        db.summaries.upsert_summary("plan.md", "hash001", "New text")
        record = db.summaries.get_summary("plan.md", "hash001")
        assert record is not None
        assert record.summary_text == "New text"

    def test_get_all_for_artifact_returns_all_hashes(self, db: PixlDB) -> None:
        """should return all summaries for an artifact across different hashes"""
        db.summaries.upsert_summary("plan.md", "hash-v1", "v1 summary")
        db.summaries.upsert_summary("plan.md", "hash-v2", "v2 summary")
        records = db.summaries.get_all_for_artifact("plan.md")
        assert len(records) == 2

    def test_delete_for_artifact_removes_all_summaries(self, db: PixlDB) -> None:
        """should delete all summaries for the given artifact name"""
        db.summaries.upsert_summary("plan.md", "hash001", "text")
        db.summaries.upsert_summary("plan.md", "hash002", "text2")
        deleted = db.summaries.delete_for_artifact("plan.md")
        assert deleted == 2
        assert db.summaries.count() == 0

    def test_count_returns_total_summaries(self, db: PixlDB) -> None:
        """should return the correct total count of summaries"""
        assert db.summaries.count() == 0
        db.summaries.upsert_summary("a.md", "h1", "text1")
        db.summaries.upsert_summary("b.md", "h2", "text2")
        assert db.summaries.count() == 2

    def test_to_dict_includes_all_fields(self, db: PixlDB) -> None:
        """should include all expected keys in to_dict() output"""
        db.summaries.upsert_summary("plan.md", "hash001", "Summary", method="llm")
        record = db.summaries.get_summary("plan.md", "hash001")
        assert record is not None
        d = record.to_dict()
        for key in ("id", "artifact_name", "source_hash", "summary_text", "method", "created_at"):
            assert key in d


# ===========================================================================
# 8. fts.py
# ===========================================================================


class TestPrepareFtsQuery:
    """Tests for the standalone prepare_fts_query() utility."""

    def test_blank_query_returns_empty_string(self) -> None:
        """should return empty string for blank input"""
        from pixl.storage.db.fts import prepare_fts_query

        assert prepare_fts_query("") == ""
        assert prepare_fts_query("   ") == ""

    def test_simple_words_joined_with_or(self) -> None:
        """should join cleaned words with OR operator"""
        from pixl.storage.db.fts import prepare_fts_query

        result = prepare_fts_query("hello world")
        assert "OR" in result
        assert "hello" in result
        assert "world" in result

    def test_fts5_syntax_passed_through(self) -> None:
        """should pass through queries that already contain FTS5 operators"""
        from pixl.storage.db.fts import prepare_fts_query

        query = '"exact phrase" AND keyword'
        assert prepare_fts_query(query) == query

    def test_or_operator_passed_through(self) -> None:
        """should pass through OR operator without modification"""
        from pixl.storage.db.fts import prepare_fts_query

        query = "foo OR bar"
        assert prepare_fts_query(query) == query

    def test_not_operator_passed_through(self) -> None:
        """should pass through NOT operator without modification"""
        from pixl.storage.db.fts import prepare_fts_query

        query = "foo NOT bar"
        assert prepare_fts_query(query) == query

    def test_short_words_filtered_out(self) -> None:
        """should filter out words shorter than 2 characters"""
        from pixl.storage.db.fts import prepare_fts_query

        result = prepare_fts_query("a bb ccc")
        assert "bb" in result
        assert "ccc" in result
        # single-char "a" should be excluded
        assert result.split(" OR ")[0] != "a"

    def test_special_chars_stripped(self) -> None:
        """should strip non-alphanumeric characters from words"""
        from pixl.storage.db.fts import prepare_fts_query

        result = prepare_fts_query("hello!")
        assert "!" not in result

    def test_all_short_words_returns_empty(self) -> None:
        """should return empty string when all words are too short"""
        from pixl.storage.db.fts import prepare_fts_query

        result = prepare_fts_query("a b c")
        assert result == ""


# ===========================================================================
# 9. chain_signals.py
# ===========================================================================


class TestChainSignalDB:
    def test_emit_signal_returns_positive_row_id(self, db: PixlDB) -> None:
        """should return a positive row ID on successful insert"""
        _seed_chain(db, "chain-001")
        row_id = db.chain_signals.emit_signal("chain-001", "node-A", "file_modified")
        assert isinstance(row_id, int)
        assert row_id > 0

    def test_emit_signal_raises_for_invalid_type(self, db: PixlDB) -> None:
        """should raise ValueError for unsupported signal_type"""
        with pytest.raises(ValueError, match="invalid signal_type"):
            db.chain_signals.emit_signal("chain-001", "node-A", "unknown_signal")

    def test_get_signals_returns_emitted_signals(self, db: PixlDB) -> None:
        """should return all signals for a chain"""
        _seed_chain(db, "chain-002")
        db.chain_signals.emit_signal("chain-002", "node-A", "discovery", {"info": "found X"})
        signals = db.chain_signals.get_signals("chain-002")
        assert len(signals) == 1
        assert signals[0]["signal_type"] == "discovery"

    def test_get_signals_with_type_filter(self, db: PixlDB) -> None:
        """should return only signals matching the specified type"""
        _seed_chain(db, "chain-003")
        db.chain_signals.emit_signal("chain-003", "node-A", "file_modified")
        db.chain_signals.emit_signal("chain-003", "node-A", "api_changed")
        signals = db.chain_signals.get_signals("chain-003", signal_type="file_modified")
        assert all(s["signal_type"] == "file_modified" for s in signals)

    def test_get_signals_with_exclude_node(self, db: PixlDB) -> None:
        """should exclude signals from the specified node"""
        _seed_chain(db, "chain-004")
        db.chain_signals.emit_signal("chain-004", "node-X", "discovery")
        db.chain_signals.emit_signal("chain-004", "node-Y", "discovery")
        signals = db.chain_signals.get_signals("chain-004", exclude_node="node-X")
        assert all(s["from_node"] != "node-X" for s in signals)

    def test_get_sibling_signals_excludes_own_node(self, db: PixlDB) -> None:
        """should not return signals from the querying node itself"""
        _seed_chain(db, "chain-005")
        db.chain_signals.emit_signal("chain-005", "node-self", "status_update")
        db.chain_signals.emit_signal("chain-005", "node-other", "status_update")
        siblings = db.chain_signals.get_sibling_signals("chain-005", "node-self")
        assert all(s["from_node"] != "node-self" for s in siblings)

    def test_get_file_claims_returns_claims_dict(self, db: PixlDB) -> None:
        """should return a mapping of file paths to claiming nodes"""
        _seed_chain(db, "chain-006")
        db.chain_signals.emit_signal(
            "chain-006", "node-A", "file_claim", {"files": ["src/app.ts"]}
        )
        claims = db.chain_signals.get_file_claims("chain-006")
        assert "src/app.ts" in claims
        assert "node-A" in claims["src/app.ts"]

    def test_delete_signals_for_chain_removes_all(self, db: PixlDB) -> None:
        """should delete all signals for a chain and return the count"""
        _seed_chain(db, "chain-del")
        db.chain_signals.emit_signal("chain-del", "node-A", "blocker")
        db.chain_signals.emit_signal("chain-del", "node-B", "blocker")
        count = db.chain_signals.delete_signals_for_chain("chain-del")
        assert count == 2
        assert db.chain_signals.get_signals("chain-del") == []

    def test_emit_signal_with_payload_stores_json(self, db: PixlDB) -> None:
        """should store payload as JSON and return it parsed"""
        _seed_chain(db, "chain-007")
        payload = {"file": "main.py", "lines": [10, 20]}
        db.chain_signals.emit_signal("chain-007", "node-A", "file_modified", payload)
        signals = db.chain_signals.get_signals("chain-007")
        assert signals[0]["payload"]["file"] == "main.py"

    def test_get_signals_returns_empty_for_unknown_chain(self, db: PixlDB) -> None:
        """should return empty list for a chain with no signals"""
        assert db.chain_signals.get_signals("no-such-chain") == []


# ===========================================================================
# 10. wakeup_queue.py
# ===========================================================================


class TestWakeupQueueDB:
    def test_enqueue_returns_request_id(self, db: PixlDB) -> None:
        """should return a positive integer request ID"""
        _seed_session(db, "sess-wq")
        req_id = db.wakeup_queue.enqueue("sess-wq", "schedule_trigger")
        assert isinstance(req_id, int)
        assert req_id > 0

    def test_dequeue_next_returns_oldest_pending(self, db: PixlDB) -> None:
        """should atomically claim the oldest pending request"""
        _seed_session(db, "sess-wq2")
        db.wakeup_queue.enqueue("sess-wq2", "reason-1")
        db.wakeup_queue.enqueue("sess-wq2", "reason-2")
        request = db.wakeup_queue.dequeue_next()
        assert request is not None
        assert request["reason"] == "reason-1"

    def test_dequeue_next_returns_none_when_queue_empty(self, db: PixlDB) -> None:
        """should return None when no pending requests exist"""
        assert db.wakeup_queue.dequeue_next() is None

    def test_complete_marks_request_completed(self, db: PixlDB) -> None:
        """should mark a processing request as completed"""
        _seed_session(db, "sess-wq3")
        req_id = db.wakeup_queue.enqueue("sess-wq3", "reason")
        db.wakeup_queue.dequeue_next()
        db.wakeup_queue.complete(req_id)
        # pending count should be 0
        assert db.wakeup_queue.pending_count("sess-wq3") == 0

    def test_fail_marks_request_failed(self, db: PixlDB) -> None:
        """should mark a request as failed"""
        _seed_session(db, "sess-wq4")
        req_id = db.wakeup_queue.enqueue("sess-wq4", "reason")
        db.wakeup_queue.dequeue_next()
        db.wakeup_queue.fail(req_id, "error occurred")
        # pending_count should not include failed
        assert db.wakeup_queue.pending_count("sess-wq4") == 0

    def test_pending_count_returns_correct_count(self, db: PixlDB) -> None:
        """should return the number of pending requests for a session"""
        _seed_session(db, "sess-wq5")
        db.wakeup_queue.enqueue("sess-wq5", "r1")
        db.wakeup_queue.enqueue("sess-wq5", "r2")
        assert db.wakeup_queue.pending_count("sess-wq5") == 2

    def test_pending_count_total_returns_all_sessions(self, db: PixlDB) -> None:
        """should return pending count across all sessions when session_id is None"""
        _seed_session(db, "sess-wq6")
        _seed_session(db, "sess-wq7")
        db.wakeup_queue.enqueue("sess-wq6", "r1")
        db.wakeup_queue.enqueue("sess-wq7", "r2")
        assert db.wakeup_queue.pending_count() == 2

    def test_coalesce_pending_reduces_to_one_per_session(self, db: PixlDB) -> None:
        """should coalesce multiple pending requests leaving only the oldest"""
        _seed_session(db, "sess-wq8")
        db.wakeup_queue.enqueue("sess-wq8", "r1")
        db.wakeup_queue.enqueue("sess-wq8", "r2")
        db.wakeup_queue.enqueue("sess-wq8", "r3")
        coalesced = db.wakeup_queue.coalesce_pending("sess-wq8")
        assert coalesced == 2
        assert db.wakeup_queue.pending_count("sess-wq8") == 1

    def test_defer_marks_request_deferred(self, db: PixlDB) -> None:
        """should mark a request as deferred"""
        _seed_session(db, "sess-wq9")
        req_id = db.wakeup_queue.enqueue("sess-wq9", "reason")
        db.wakeup_queue.defer(req_id)
        # deferred should not show up in pending count
        assert db.wakeup_queue.pending_count("sess-wq9") == 0

    def test_promote_deferred_restores_pending(self, db: PixlDB) -> None:
        """should promote deferred requests back to pending status"""
        _seed_session(db, "sess-wq10")
        req_id = db.wakeup_queue.enqueue("sess-wq10", "reason")
        db.wakeup_queue.defer(req_id)
        promoted = db.wakeup_queue.promote_deferred("sess-wq10")
        assert promoted == 1
        assert db.wakeup_queue.pending_count("sess-wq10") == 1

    def test_has_active_processing_returns_false_initially(self, db: PixlDB) -> None:
        """should return False when no requests are being processed"""
        _seed_session(db, "sess-wq11")
        assert db.wakeup_queue.has_active_processing("sess-wq11") is False

    def test_enqueue_with_payload_stores_json(self, db: PixlDB) -> None:
        """should store payload JSON alongside the request"""
        _seed_session(db, "sess-wq12")
        payload = {"key": "value"}
        db.wakeup_queue.enqueue("sess-wq12", "reason", payload=payload)
        request = db.wakeup_queue.dequeue_next()
        assert request is not None
        # payload_json field should contain the JSON string
        assert "key" in request["payload_json"]

    def test_promote_orphaned_deferred_no_crash_when_empty(self, db: PixlDB) -> None:
        """should return 0 and not crash when there are no deferred requests"""
        count = db.wakeup_queue.promote_orphaned_deferred()
        assert count == 0


# ===========================================================================
# 11. task_sessions.py
# ===========================================================================


class TestTaskSessionDB:
    def test_get_task_session_returns_none_for_missing(self, db: PixlDB) -> None:
        """should return None when no task session exists for the given key"""
        assert db.task_sessions.get_task_session("sess-ts", "task-key") is None

    def test_upsert_creates_new_task_session(self, db: PixlDB) -> None:
        """should create a new task session record"""
        _seed_session(db, "sess-ts")
        db.task_sessions.upsert_task_session(
            session_id="sess-ts",
            node_id="node-1",
            task_key="my-task",
            adapter_name="claude_code",
        )
        record = db.task_sessions.get_task_session("sess-ts", "my-task")
        assert record is not None
        assert record["adapter_name"] == "claude_code"

    def test_upsert_updates_existing_task_session(self, db: PixlDB) -> None:
        """should update an existing task session when the same key is upserted"""
        _seed_session(db, "sess-ts2")
        db.task_sessions.upsert_task_session(
            session_id="sess-ts2",
            node_id="node-1",
            task_key="my-task",
            adapter_name="claude_code",
            adapter_session_id="as-001",
        )
        db.task_sessions.upsert_task_session(
            session_id="sess-ts2",
            node_id="node-1",
            task_key="my-task",
            adapter_name="claude_code",
            adapter_session_id="as-002",
        )
        record = db.task_sessions.get_task_session("sess-ts2", "my-task")
        assert record is not None
        assert record["adapter_session_id"] == "as-002"

    def test_upsert_stores_last_run_id(self, db: PixlDB) -> None:
        """should persist last_run_id on the task session"""
        _seed_session(db, "sess-ts3")
        db.task_sessions.upsert_task_session(
            session_id="sess-ts3",
            node_id="node-1",
            task_key="task-w-run",
            adapter_name="claude_code",
            last_run_id="run-xyz",
        )
        record = db.task_sessions.get_task_session("sess-ts3", "task-w-run")
        assert record is not None
        assert record["last_run_id"] == "run-xyz"

    def test_different_task_keys_are_independent(self, db: PixlDB) -> None:
        """should store separate records for different task keys within the same session"""
        _seed_session(db, "sess-ts4")
        db.task_sessions.upsert_task_session("sess-ts4", "node-1", "task-A", "adapter-1")
        db.task_sessions.upsert_task_session("sess-ts4", "node-1", "task-B", "adapter-2")
        record_a = db.task_sessions.get_task_session("sess-ts4", "task-A")
        record_b = db.task_sessions.get_task_session("sess-ts4", "task-B")
        assert record_a is not None
        assert record_b is not None
        assert record_a["adapter_name"] == "adapter-1"
        assert record_b["adapter_name"] == "adapter-2"
