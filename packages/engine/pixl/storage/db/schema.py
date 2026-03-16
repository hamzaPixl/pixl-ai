"""SQLite schema definitions for Pixl.

Design principles:
- Proper FK constraints for roadmap -> epic -> feature hierarchy
- FTS5 virtual tables for RAG-friendly search on knowledge + artifacts
- Event sourcing table for complete audit trail of state transitions
- JSON columns for semi-structured data (node_instances, milestones, etc.)
- Indexed queries on status, parent IDs, timestamps
- Schema versioning with migration support

The schema is designed to replace ALL existing JSON file stores:
- backlog.json        -> roadmaps, epics, features, feature_dependencies, milestones, notes
- chunks.json         -> documents, chunks + chunks_fts (FTS5)
- sessions/*.json     -> workflow_sessions, node_instances, loop_states
- events.jsonl        -> events (unified across all sessions)
- artifacts/          -> artifacts + artifacts_fts (FTS5)
- config.json         -> config
"""

SCHEMA_VERSION = 34

_SCHEMA_SQL = """
-- ============================================================================
-- Schema versioning
-- ============================================================================

CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER PRIMARY KEY,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    migrated_at TEXT
);

-- ============================================================================
-- Core hierarchy: Roadmap -> Epic -> Feature
-- ============================================================================

CREATE TABLE IF NOT EXISTS roadmaps (
    id               TEXT PRIMARY KEY,  -- roadmap-NNN
    title            TEXT NOT NULL,
    original_prompt  TEXT NOT NULL DEFAULT '',
    status           TEXT NOT NULL DEFAULT 'drafting'
                     CHECK (status IN ('drafting', 'planned', 'in_progress', 'completed')),
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at       TEXT,
    completed_at     TEXT
);
CREATE INDEX IF NOT EXISTS idx_roadmaps_status ON roadmaps(status);

CREATE TABLE IF NOT EXISTS milestones (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    roadmap_id   TEXT NOT NULL REFERENCES roadmaps(id) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    target_date  TEXT,  -- ISO date
    sort_order   INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_milestones_roadmap ON milestones(roadmap_id);

CREATE TABLE IF NOT EXISTS milestone_dependencies (
    milestone_id  INTEGER NOT NULL REFERENCES milestones(id) ON DELETE CASCADE,
    depends_on_id INTEGER NOT NULL REFERENCES milestones(id) ON DELETE CASCADE,
    PRIMARY KEY (milestone_id, depends_on_id),
    CHECK (milestone_id != depends_on_id)
);
CREATE INDEX IF NOT EXISTS idx_milestone_deps_milestone ON milestone_dependencies(milestone_id);
CREATE INDEX IF NOT EXISTS idx_milestone_deps_depends ON milestone_dependencies(depends_on_id);

CREATE TABLE IF NOT EXISTS epics (
    id               TEXT PRIMARY KEY,  -- epic-NNN
    roadmap_id       TEXT REFERENCES roadmaps(id) ON DELETE SET NULL,
    milestone_id     INTEGER REFERENCES milestones(id) ON DELETE SET NULL,
    title            TEXT NOT NULL,
    original_prompt  TEXT NOT NULL DEFAULT '',
    workflow_id      TEXT,
    outcome          TEXT NOT NULL DEFAULT '',
    kpis_json        TEXT NOT NULL DEFAULT '[]',
    status           TEXT NOT NULL DEFAULT 'drafting'
                     CHECK (status IN ('drafting', 'decomposed', 'in_progress', 'completed', 'failed')),
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at       TEXT,
    completed_at     TEXT
);
CREATE INDEX IF NOT EXISTS idx_epics_status ON epics(status);
CREATE INDEX IF NOT EXISTS idx_epics_roadmap ON epics(roadmap_id);

CREATE TABLE IF NOT EXISTS features (
    id              TEXT PRIMARY KEY,  -- feat-NNN
    epic_id         TEXT REFERENCES epics(id) ON DELETE SET NULL,
    roadmap_id      TEXT REFERENCES roadmaps(id) ON DELETE SET NULL,
    title           TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    type            TEXT NOT NULL DEFAULT 'feature'
                    CHECK (type IN ('feature', 'bug', 'refactor', 'docs', 'chore', 'execution')),
    priority        TEXT NOT NULL DEFAULT 'P2'
                    CHECK (priority IN ('P0', 'P1', 'P2', 'P3')),
    status          TEXT NOT NULL DEFAULT 'backlog'
                    CHECK (status IN ('backlog', 'planned', 'in_progress', 'review', 'blocked', 'done', 'failed')),

    -- Timestamps
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT,
    planned_at      TEXT,
    started_at      TEXT,
    completed_at    TEXT,

    -- Blocking info
    blocked_by      TEXT,
    blocked_reason  TEXT,

    -- Tracking
    plan_path       TEXT,
    pr_url          TEXT,
    branch_name     TEXT,
    owner           TEXT,
    risk_class      TEXT CHECK (risk_class IN ('low', 'medium', 'high', 'critical')),
    estimate_points INTEGER NOT NULL DEFAULT 1 CHECK (estimate_points >= 1),

    -- Metrics
    estimated_hours REAL,
    actual_hours    REAL,
    total_cost_usd  REAL NOT NULL DEFAULT 0.0,
    total_tokens    INTEGER NOT NULL DEFAULT 0,

    -- Verification metadata (GAP-02 / GAP-13)
    acceptance_criteria_json TEXT NOT NULL DEFAULT '[]',
    success_criteria_json TEXT NOT NULL DEFAULT '[]',
    assumptions_json      TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS idx_features_status ON features(status);
CREATE INDEX IF NOT EXISTS idx_features_epic ON features(epic_id);
CREATE INDEX IF NOT EXISTS idx_features_roadmap ON features(roadmap_id);
CREATE INDEX IF NOT EXISTS idx_features_priority ON features(priority);

CREATE TABLE IF NOT EXISTS feature_dependencies (
    feature_id    TEXT NOT NULL REFERENCES features(id) ON DELETE CASCADE,
    depends_on_id TEXT NOT NULL REFERENCES features(id) ON DELETE CASCADE,
    PRIMARY KEY (feature_id, depends_on_id),
    CHECK (feature_id != depends_on_id)
);
CREATE INDEX IF NOT EXISTS idx_deps_feature ON feature_dependencies(feature_id);
CREATE INDEX IF NOT EXISTS idx_deps_depends ON feature_dependencies(depends_on_id);

-- Polymorphic notes for any entity type
CREATE TABLE IF NOT EXISTS notes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('roadmap', 'epic', 'feature')),
    entity_id   TEXT NOT NULL,
    content     TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_notes_entity ON notes(entity_type, entity_id);

-- ============================================================================
-- State transitions (event sourcing / audit log)
-- ============================================================================

CREATE TABLE IF NOT EXISTS state_transitions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type   TEXT NOT NULL CHECK (entity_type IN ('roadmap', 'epic', 'feature', 'session')),
    entity_id     TEXT NOT NULL,
    from_status   TEXT,       -- NULL for initial creation
    to_status     TEXT NOT NULL,
    trigger       TEXT,       -- What caused the transition (workflow, user, system)
    trigger_id    TEXT,       -- Session ID or user action that caused it
    metadata      TEXT,       -- JSON blob for extra context
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_transitions_entity ON state_transitions(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_transitions_time ON state_transitions(created_at);

-- ============================================================================
-- Workflow sessions & execution state
-- ============================================================================

CREATE TABLE IF NOT EXISTS workflow_sessions (
    id                TEXT PRIMARY KEY,  -- sess-XXXX
    feature_id        TEXT REFERENCES features(id) ON DELETE SET NULL,
    snapshot_hash     TEXT NOT NULL,
    schema_version    INTEGER NOT NULL DEFAULT 1,

    -- Timing
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    started_at        TEXT,
    ended_at          TEXT,
    last_updated_at   TEXT,

    -- Git baseline
    baseline_commit   TEXT,
    workspace_root    TEXT,

    -- Cursor state (JSON)
    cursor_json       TEXT,  -- ExecutorCursor serialized

    -- Pause state (v2)
    paused_at         TEXT,
    pause_reason      TEXT,

    -- Frozen artifacts (JSON: {path: sha256})
    frozen_artifacts  TEXT NOT NULL DEFAULT '{}',

    -- Structured context mode state (JSON)
    structured_outputs_json TEXT NOT NULL DEFAULT '{}',
    session_state_json      TEXT NOT NULL DEFAULT '{}',

    -- Baton context (for context_mode: baton)
    baton_json            TEXT,
    baton_history_json    TEXT NOT NULL DEFAULT '[]',
    context_audit_json    TEXT NOT NULL DEFAULT '[]',

    -- Heartbeat execution state
    status                TEXT DEFAULT 'created',
    current_run_id        TEXT
);
CREATE INDEX IF NOT EXISTS idx_sessions_feature ON workflow_sessions(feature_id);
CREATE INDEX IF NOT EXISTS idx_sessions_created ON workflow_sessions(created_at);

CREATE TABLE IF NOT EXISTS node_instances (
    session_id     TEXT NOT NULL REFERENCES workflow_sessions(id) ON DELETE CASCADE,
    node_id        TEXT NOT NULL,
    state          TEXT NOT NULL CHECK (state IN (
                       'task_pending', 'task_running', 'task_completed', 'task_failed',
                       'task_blocked', 'task_skipped', 'task_timeout',
                       'gate_waiting', 'gate_approved', 'gate_rejected', 'gate_timeout'
                   )),
    attempt        INTEGER NOT NULL DEFAULT 0,
    ready_at       TEXT,
    started_at     TEXT,
    ended_at       TEXT,
    blocked_reason TEXT,
    output_json    TEXT,  -- JSON blob for node output/result
    failure_kind   TEXT,  -- e.g. "transient", "fatal"
    error_message  TEXT,  -- Human-readable error description
    model_name     TEXT,  -- Effective model used for this node
    agent_name     TEXT,  -- Agent that executed this node
    input_tokens   INTEGER NOT NULL DEFAULT 0,
    output_tokens  INTEGER NOT NULL DEFAULT 0,
    total_tokens   INTEGER NOT NULL DEFAULT 0,
    cost_usd       REAL NOT NULL DEFAULT 0.0,
    execution_run_id    TEXT,
    execution_locked_at TEXT,
    metadata_json  TEXT NOT NULL DEFAULT '{}',  -- Additional node runtime metadata
    PRIMARY KEY (session_id, node_id)
);
CREATE INDEX IF NOT EXISTS idx_node_state ON node_instances(state);

CREATE TABLE IF NOT EXISTS loop_states (
    session_id        TEXT NOT NULL REFERENCES workflow_sessions(id) ON DELETE CASCADE,
    loop_id           TEXT NOT NULL,
    current_iteration INTEGER NOT NULL DEFAULT 0,
    max_iterations    INTEGER NOT NULL DEFAULT 3,
    history_json      TEXT NOT NULL DEFAULT '[]',  -- JSON array of iteration records
    PRIMARY KEY (session_id, loop_id)
);

CREATE TABLE IF NOT EXISTS workflow_snapshots (
    snapshot_hash  TEXT PRIMARY KEY,
    snapshot_json  TEXT NOT NULL,  -- Full WorkflowSnapshot serialized
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================================
-- Events (unified event log, replaces per-session events.jsonl)
-- ============================================================================

CREATE TABLE IF NOT EXISTS events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   TEXT REFERENCES workflow_sessions(id) ON DELETE CASCADE,
    event_type   TEXT NOT NULL,
    node_id      TEXT,
    entity_type  TEXT,  -- roadmap, epic, feature (for non-session events)
    entity_id    TEXT,
    payload_json TEXT,  -- JSON blob with event-specific data
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_entity ON events(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_events_time ON events(created_at);

-- ============================================================================
-- Artifacts (with FTS5 for RAG search)
-- ============================================================================

CREATE TABLE IF NOT EXISTS artifacts (
    id            TEXT PRIMARY KEY,  -- art-XXXX
    type          TEXT NOT NULL DEFAULT 'other'
                  CHECK (type IN ('document', 'code', 'test', 'review', 'plan',
                                  'context', 'requirement', 'diagram', 'log', 'progress', 'other')),
    name          TEXT NOT NULL,
    path          TEXT,            -- Relative path to artifact file

    -- Content (DB-canonical; inline for small, chunked for large payloads)
    content       TEXT,            -- Inline text content (or searchable preview for chunked)
    content_hash  TEXT,            -- SHA256 of content
    logical_hash  TEXT,            -- Normalized content hash
    storage_mode  TEXT NOT NULL DEFAULT 'inline'
                  CHECK (storage_mode IN ('inline', 'chunked')),
    chunk_count   INTEGER NOT NULL DEFAULT 0,
    uncompressed_size_bytes INTEGER,
    compressed_size_bytes   INTEGER,

    -- Provenance
    task_id       TEXT,            -- Workflow node that produced this
    session_id    TEXT REFERENCES workflow_sessions(id) ON DELETE SET NULL,
    feature_id    TEXT REFERENCES features(id) ON DELETE SET NULL,
    epic_id       TEXT REFERENCES epics(id) ON DELETE SET NULL,

    -- Metadata
    size_bytes    INTEGER,
    mime_type     TEXT,
    tags_json     TEXT NOT NULL DEFAULT '[]',   -- JSON array of tags
    extra_json    TEXT NOT NULL DEFAULT '{}',    -- JSON blob
    references_json TEXT NOT NULL DEFAULT '[]',  -- Related artifact IDs

    -- Versioning (added in v6)
    version               TEXT DEFAULT '1.0.0',
    version_major         INTEGER DEFAULT 1,
    version_minor         INTEGER DEFAULT 0,
    version_patch         INTEGER DEFAULT 0,
    previous_version_id   TEXT,
    change_description    TEXT,

    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_artifacts_type ON artifacts(type);
CREATE INDEX IF NOT EXISTS idx_artifacts_session ON artifacts(session_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_feature ON artifacts(feature_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_hash ON artifacts(content_hash);
CREATE INDEX IF NOT EXISTS idx_artifacts_task ON artifacts(task_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_epic ON artifacts(epic_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_version ON artifacts(path, version_major, version_minor, version_patch);
CREATE INDEX IF NOT EXISTS idx_artifacts_previous_version ON artifacts(previous_version_id);

CREATE TABLE IF NOT EXISTS artifact_chunks (
    artifact_id          TEXT NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
    chunk_index          INTEGER NOT NULL,
    payload_compressed   BLOB NOT NULL,
    payload_size_bytes   INTEGER NOT NULL,
    PRIMARY KEY (artifact_id, chunk_index)
);
-- FTS5 virtual table for artifact content search
CREATE VIRTUAL TABLE IF NOT EXISTS artifacts_fts USING fts5(
    name,
    content,
    tags,              -- Space-separated tags for boosting
    content=artifacts,
    content_rowid=rowid,
    tokenize='porter unicode61'
);

-- Triggers to keep FTS5 index in sync with artifacts table
CREATE TRIGGER IF NOT EXISTS artifacts_ai AFTER INSERT ON artifacts BEGIN
    INSERT INTO artifacts_fts(rowid, name, content, tags)
    VALUES (NEW.rowid, NEW.name, COALESCE(NEW.content, ''), COALESCE(NEW.tags_json, ''));
END;

CREATE TRIGGER IF NOT EXISTS artifacts_ad AFTER DELETE ON artifacts BEGIN
    INSERT INTO artifacts_fts(artifacts_fts, rowid, name, content, tags)
    VALUES ('delete', OLD.rowid, OLD.name, COALESCE(OLD.content, ''), COALESCE(OLD.tags_json, ''));
END;

CREATE TRIGGER IF NOT EXISTS artifacts_au AFTER UPDATE ON artifacts BEGIN
    INSERT INTO artifacts_fts(artifacts_fts, rowid, name, content, tags)
    VALUES ('delete', OLD.rowid, OLD.name, COALESCE(OLD.content, ''), COALESCE(OLD.tags_json, ''));
    INSERT INTO artifacts_fts(rowid, name, content, tags)
    VALUES (NEW.rowid, NEW.name, COALESCE(NEW.content, ''), COALESCE(NEW.tags_json, ''));
END;

-- ============================================================================
-- Knowledge / RAG (with FTS5 for semantic-ish search)
-- ============================================================================

CREATE TABLE IF NOT EXISTS documents (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    path         TEXT NOT NULL UNIQUE,  -- Relative file path
    content_hash TEXT NOT NULL,         -- SHA256 for change detection
    chunk_count  INTEGER NOT NULL DEFAULT 0,
    indexed_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_docs_path ON documents(path);

CREATE TABLE IF NOT EXISTS chunks (
    id          TEXT PRIMARY KEY,     -- {source}:{title} normalized
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    content     TEXT NOT NULL,
    source      TEXT NOT NULL,        -- File path
    chunk_type  TEXT NOT NULL DEFAULT 'concept'
                CHECK (chunk_type IN ('concept', 'procedure', 'reference', 'code')),
    keywords    TEXT NOT NULL DEFAULT '',  -- Space-separated keywords
    line_start  INTEGER,
    line_end    INTEGER,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_type ON chunks(chunk_type);
CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source);

-- FTS5 virtual table for knowledge search
-- BM25 ranking replaces custom TF-IDF implementation
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    title,
    content,
    keywords,
    source,
    content=chunks,
    content_rowid=rowid,
    tokenize='porter unicode61'
);

-- Triggers to keep FTS5 in sync
CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, title, content, keywords, source)
    VALUES (NEW.rowid, NEW.title, NEW.content, NEW.keywords, NEW.source);
END;

CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, title, content, keywords, source)
    VALUES ('delete', OLD.rowid, OLD.title, OLD.content, OLD.keywords, OLD.source);
END;

CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, title, content, keywords, source)
    VALUES ('delete', OLD.rowid, OLD.title, OLD.content, OLD.keywords, OLD.source);
    INSERT INTO chunks_fts(rowid, title, content, keywords, source)
    VALUES (NEW.rowid, NEW.title, NEW.content, NEW.keywords, NEW.source);
END;

-- Knowledge build manifest
CREATE TABLE IF NOT EXISTS knowledge_manifest (
    id              INTEGER PRIMARY KEY CHECK (id = 1),  -- Singleton
    version         TEXT NOT NULL DEFAULT '1.0',
    last_build      TEXT,
    chunk_count     INTEGER NOT NULL DEFAULT 0,
    source_count    INTEGER NOT NULL DEFAULT 0,
    build_duration_ms INTEGER NOT NULL DEFAULT 0
);

-- ============================================================================
-- Agent performance metrics
-- ============================================================================

CREATE TABLE IF NOT EXISTS agent_metrics (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name      TEXT NOT NULL,
    model_name      TEXT NOT NULL,
    session_id      TEXT NOT NULL REFERENCES workflow_sessions(id) ON DELETE CASCADE,
    node_id         TEXT NOT NULL,
    feature_id      TEXT REFERENCES features(id) ON DELETE SET NULL,
    started_at      TEXT NOT NULL,
    completed_at    TEXT,
    input_tokens    INTEGER NOT NULL DEFAULT 0,
    output_tokens   INTEGER NOT NULL DEFAULT 0,
    total_tokens    INTEGER NOT NULL DEFAULT 0,
    total_cost_usd  REAL NOT NULL DEFAULT 0.0,
    success         INTEGER NOT NULL DEFAULT 1,
    error_type      TEXT,
    error_message   TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_agent_metrics_agent ON agent_metrics(agent_name);
CREATE INDEX IF NOT EXISTS idx_agent_metrics_model ON agent_metrics(model_name);
CREATE INDEX IF NOT EXISTS idx_agent_metrics_session ON agent_metrics(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_metrics_feature ON agent_metrics(feature_id);
CREATE INDEX IF NOT EXISTS idx_agent_metrics_started ON agent_metrics(started_at);
CREATE INDEX IF NOT EXISTS idx_agent_metrics_success ON agent_metrics(success);

-- ============================================================================
-- Configuration
-- ============================================================================

CREATE TABLE IF NOT EXISTS config (
    key    TEXT PRIMARY KEY,
    value  TEXT NOT NULL,  -- JSON value
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================================
-- Incident tracking for recovery history
-- ============================================================================

CREATE TABLE IF NOT EXISTS incidents (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES workflow_sessions(id) ON DELETE CASCADE,
    node_id TEXT,
    feature_id TEXT,
    error_type TEXT NOT NULL,
    error_message TEXT NOT NULL,
    recovery_action TEXT,
    outcome TEXT NOT NULL CHECK (outcome IN ('succeeded', 'failed', 'escalated')),
    attempt_count INTEGER NOT NULL DEFAULT 0,
    payload_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    resolved_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_incidents_error_type ON incidents(error_type);
CREATE INDEX IF NOT EXISTS idx_incidents_outcome ON incidents(outcome);
CREATE INDEX IF NOT EXISTS idx_incidents_session ON incidents(session_id);
CREATE INDEX IF NOT EXISTS idx_incidents_feature ON incidents(feature_id);
CREATE INDEX IF NOT EXISTS idx_incidents_created_at ON incidents(created_at DESC);

-- FTS5 virtual table for similarity search
CREATE VIRTUAL TABLE IF NOT EXISTS incidents_fts USING fts5(
    error_type,
    error_message,
    content='incidents',
    content_rowid=rowid,
    tokenize='porter unicode61'
);

-- Triggers to keep FTS5 index in sync
CREATE TRIGGER IF NOT EXISTS incidents_ai AFTER INSERT ON incidents BEGIN
    INSERT INTO incidents_fts(rowid, error_type, error_message)
    VALUES (NEW.rowid, NEW.error_type, NEW.error_message);
END;

CREATE TRIGGER IF NOT EXISTS incidents_ad AFTER DELETE ON incidents BEGIN
    INSERT INTO incidents_fts(incidents_fts, rowid, error_type, error_message)
    VALUES ('delete', OLD.rowid, OLD.error_type, OLD.error_message);
END;

CREATE TRIGGER IF NOT EXISTS incidents_au AFTER UPDATE ON incidents BEGIN
    INSERT INTO incidents_fts(incidents_fts, rowid, error_type, error_message)
    VALUES ('delete', OLD.rowid, OLD.error_type, OLD.error_message);
    INSERT INTO incidents_fts(rowid, error_type, error_message)
    VALUES (NEW.rowid, NEW.error_type, NEW.error_message);
END;

-- ============================================================================
-- Autonomy confidence profiles
-- ============================================================================

CREATE TABLE IF NOT EXISTS autonomy_profiles (
    feature_id     TEXT NOT NULL REFERENCES features(id) ON DELETE CASCADE,
    agent_name     TEXT NOT NULL,
    task_key       TEXT NOT NULL,
    mode           TEXT NOT NULL DEFAULT 'assist'
                   CHECK (mode IN ('assist', 'autopilot')),
    level          INTEGER NOT NULL DEFAULT 0
                   CHECK (level >= 0 AND level <= 3),
    confidence     REAL NOT NULL DEFAULT 0.0,
    samples        INTEGER NOT NULL DEFAULT 0,
    last_reason    TEXT,
    updated_at     TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (feature_id, agent_name, task_key)
);
CREATE INDEX IF NOT EXISTS idx_autonomy_profiles_feature ON autonomy_profiles(feature_id);
CREATE INDEX IF NOT EXISTS idx_autonomy_profiles_level ON autonomy_profiles(level);

CREATE TABLE IF NOT EXISTS autonomy_outcomes (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id            TEXT NOT NULL UNIQUE REFERENCES workflow_sessions(id) ON DELETE CASCADE,
    feature_id            TEXT REFERENCES features(id) ON DELETE SET NULL,
    agent_name            TEXT NOT NULL DEFAULT 'unknown',
    task_key              TEXT NOT NULL DEFAULT 'workflow',
    mode                  TEXT NOT NULL DEFAULT 'assist'
                          CHECK (mode IN ('assist', 'autopilot')),
    level                 INTEGER NOT NULL DEFAULT 0 CHECK (level >= 0 AND level <= 3),
    confidence            REAL NOT NULL DEFAULT 0.0,
    samples               INTEGER NOT NULL DEFAULT 0,
    auto_approved_gates   INTEGER NOT NULL DEFAULT 0,
    manual_gate_approvals INTEGER NOT NULL DEFAULT 0,
    gate_rejections       INTEGER NOT NULL DEFAULT 0,
    recovery_cycles       INTEGER NOT NULL DEFAULT 0,
    human_interventions   INTEGER NOT NULL DEFAULT 0,
    created_at            TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_autonomy_outcomes_feature ON autonomy_outcomes(feature_id);
CREATE INDEX IF NOT EXISTS idx_autonomy_outcomes_created ON autonomy_outcomes(created_at DESC);

-- ============================================================================
-- Session LLM report jobs
-- ============================================================================

CREATE TABLE IF NOT EXISTS session_report_jobs (
    id               TEXT PRIMARY KEY,
    session_id       TEXT NOT NULL REFERENCES workflow_sessions(id) ON DELETE CASCADE,
    trigger          TEXT NOT NULL CHECK (trigger IN ('manual_draft', 'auto_terminal')),
    terminal_status  TEXT CHECK (terminal_status IN ('completed', 'failed')),
    status           TEXT NOT NULL DEFAULT 'queued'
                     CHECK (status IN ('queued', 'running', 'completed', 'failed')),
    requested_by     TEXT,
    artifact_id      TEXT REFERENCES artifacts(id) ON DELETE SET NULL,
    error_message    TEXT,
    retry_count      INTEGER NOT NULL DEFAULT 0,
    idempotency_key  TEXT UNIQUE,
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    started_at       TEXT,
    completed_at     TEXT,
    updated_at       TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_session_report_jobs_session_created
    ON session_report_jobs(session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_session_report_jobs_status_created
    ON session_report_jobs(status, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_session_report_jobs_trigger_terminal_created
    ON session_report_jobs(trigger, terminal_status, created_at DESC);

-- ============================================================================
-- Plan-only chain runner persistence
-- ============================================================================

CREATE TABLE IF NOT EXISTS execution_chains (
    id                      TEXT PRIMARY KEY,
    epic_id                 TEXT NOT NULL REFERENCES epics(id) ON DELETE CASCADE,
    source_session_id       TEXT REFERENCES workflow_sessions(id) ON DELETE SET NULL,
    mode                    TEXT NOT NULL DEFAULT 'plan_only'
                            CHECK (mode IN ('plan_only')),
    status                  TEXT NOT NULL DEFAULT 'plan_draft'
                            CHECK (
                                status IN (
                                    'plan_draft',
                                    'plan_ready',
                                    'running',
                                    'paused',
                                    'completed',
                                    'failed',
                                    'cancelled'
                                )
                            ),
    max_parallel            INTEGER NOT NULL DEFAULT 1,
    failure_policy          TEXT NOT NULL DEFAULT 'branch_aware',
    stop_on_failure         INTEGER NOT NULL DEFAULT 0 CHECK (stop_on_failure IN (0, 1)),
    validation_summary_json TEXT NOT NULL DEFAULT '{}',
    created_at              TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at              TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_execution_chains_epic ON execution_chains(epic_id);
CREATE INDEX IF NOT EXISTS idx_execution_chains_status ON execution_chains(status);

CREATE TABLE IF NOT EXISTS execution_chain_nodes (
    chain_id         TEXT NOT NULL REFERENCES execution_chains(id) ON DELETE CASCADE,
    node_id          TEXT NOT NULL,
    feature_id       TEXT REFERENCES features(id) ON DELETE SET NULL,
    feature_ref      TEXT NOT NULL,
    wave             INTEGER NOT NULL DEFAULT 0,
    parallel_group   INTEGER NOT NULL DEFAULT 0,
    owner            TEXT,
    risk_class       TEXT CHECK (risk_class IN ('low', 'medium', 'high', 'critical')),
    estimate_points  INTEGER,
    status           TEXT NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending', 'running', 'completed', 'failed', 'blocked', 'cancelled')),
    session_id       TEXT,
    attempt_count    INTEGER NOT NULL DEFAULT 0,
    started_at       TEXT,
    completed_at     TEXT,
    error            TEXT,
    metadata_json    TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (chain_id, node_id)
);
CREATE INDEX IF NOT EXISTS idx_execution_chain_nodes_chain ON execution_chain_nodes(chain_id);
CREATE INDEX IF NOT EXISTS idx_execution_chain_nodes_wave ON execution_chain_nodes(chain_id, wave);
CREATE INDEX IF NOT EXISTS idx_execution_chain_nodes_feature ON execution_chain_nodes(feature_id);
CREATE INDEX IF NOT EXISTS idx_execution_chain_nodes_status ON execution_chain_nodes(chain_id, status);
CREATE INDEX IF NOT EXISTS idx_execution_chain_nodes_session ON execution_chain_nodes(session_id);

CREATE TABLE IF NOT EXISTS execution_chain_edges (
    chain_id      TEXT NOT NULL REFERENCES execution_chains(id) ON DELETE CASCADE,
    from_node_id  TEXT NOT NULL,
    to_node_id    TEXT NOT NULL,
    PRIMARY KEY (chain_id, from_node_id, to_node_id),
    CHECK (from_node_id != to_node_id)
);
CREATE INDEX IF NOT EXISTS idx_execution_chain_edges_chain ON execution_chain_edges(chain_id);

-- ============================================================================
-- Chain signals (inter-agent shared state for swarm coordination)
-- ============================================================================

CREATE TABLE IF NOT EXISTS chain_signals (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chain_id    TEXT NOT NULL REFERENCES execution_chains(id) ON DELETE CASCADE,
    from_node   TEXT NOT NULL,
    signal_type TEXT NOT NULL
                CHECK (signal_type IN (
                    'file_modified', 'api_changed', 'blocker', 'discovery',
                    'status_update', 'file_claim', 'judge_finding'
                )),
    payload     TEXT NOT NULL DEFAULT '{}',
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_chain_signals_chain ON chain_signals(chain_id);
CREATE INDEX IF NOT EXISTS idx_chain_signals_type ON chain_signals(chain_id, signal_type);
CREATE INDEX IF NOT EXISTS idx_chain_signals_node ON chain_signals(from_node);
CREATE INDEX IF NOT EXISTS idx_chain_signals_created ON chain_signals(created_at);

-- FTS5 for chain signal payload search
CREATE VIRTUAL TABLE IF NOT EXISTS chain_signals_fts USING fts5(
    signal_type,
    payload,
    content=chain_signals,
    content_rowid=rowid,
    tokenize='porter unicode61'
);

-- Triggers to keep FTS5 in sync with chain_signals
CREATE TRIGGER IF NOT EXISTS chain_signals_ai AFTER INSERT ON chain_signals BEGIN
    INSERT INTO chain_signals_fts(rowid, signal_type, payload)
    VALUES (NEW.rowid, NEW.signal_type, NEW.payload);
END;

CREATE TRIGGER IF NOT EXISTS chain_signals_ad AFTER DELETE ON chain_signals BEGIN
    INSERT INTO chain_signals_fts(chain_signals_fts, rowid, signal_type, payload)
    VALUES ('delete', OLD.rowid, OLD.signal_type, OLD.payload);
END;

CREATE TRIGGER IF NOT EXISTS chain_signals_au AFTER UPDATE ON chain_signals BEGIN
    INSERT INTO chain_signals_fts(chain_signals_fts, rowid, signal_type, payload)
    VALUES ('delete', OLD.rowid, OLD.signal_type, OLD.payload);
    INSERT INTO chain_signals_fts(rowid, signal_type, payload)
    VALUES (NEW.rowid, NEW.signal_type, NEW.payload);
END;

-- ============================================================================
-- Quality scores (swarm quality metrics over time)
-- ============================================================================

CREATE TABLE IF NOT EXISTS quality_scores (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    scope_type  TEXT NOT NULL
                CHECK (scope_type IN ('chain', 'node', 'session', 'feature', 'epic')),
    scope_id    TEXT NOT NULL,
    metric      TEXT NOT NULL,
    value       REAL NOT NULL,
    measured_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_quality_scores_scope ON quality_scores(scope_type, scope_id);
CREATE INDEX IF NOT EXISTS idx_quality_scores_metric ON quality_scores(metric);
CREATE INDEX IF NOT EXISTS idx_quality_scores_measured ON quality_scores(measured_at);

-- ============================================================================
-- ID sequence generators (replaces next_id, next_epic_id, next_roadmap_id)
-- ============================================================================

CREATE TABLE IF NOT EXISTS id_sequences (
    name       TEXT PRIMARY KEY,
    next_value INTEGER NOT NULL DEFAULT 1
);

-- Initialize sequences
INSERT OR IGNORE INTO id_sequences (name, next_value) VALUES ('feature', 1);
INSERT OR IGNORE INTO id_sequences (name, next_value) VALUES ('epic', 1);
INSERT OR IGNORE INTO id_sequences (name, next_value) VALUES ('roadmap', 1);

-- ============================================================================
-- Artifact summary cache (context intelligence layer)
-- ============================================================================

CREATE TABLE IF NOT EXISTS artifact_summaries (
    id              TEXT PRIMARY KEY,
    artifact_name   TEXT NOT NULL,
    source_hash     TEXT NOT NULL,
    summary_text    TEXT NOT NULL,
    summary_tokens  INTEGER NOT NULL DEFAULT 0,
    method          TEXT NOT NULL DEFAULT 'heuristic',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(artifact_name, source_hash)
);
CREATE INDEX IF NOT EXISTS idx_summaries_lookup ON artifact_summaries(artifact_name, source_hash);

-- ============================================================================
-- Heartbeat runs (execution windows)
-- ============================================================================

CREATE TABLE IF NOT EXISTS heartbeat_runs (
    id              TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL REFERENCES workflow_sessions(id) ON DELETE CASCADE,
    status          TEXT NOT NULL DEFAULT 'queued'
                    CHECK (status IN ('queued','running','succeeded','failed','cancelled','timed_out')),
    invocation      TEXT NOT NULL DEFAULT 'start'
                    CHECK (invocation IN ('start','resume','retry','gate_approved','chain')),
    started_at      TEXT,
    ended_at        TEXT,
    heartbeat_at    TEXT,
    input_tokens    INTEGER DEFAULT 0,
    output_tokens   INTEGER DEFAULT 0,
    cost_usd        REAL DEFAULT 0.0,
    steps_executed  INTEGER DEFAULT 0,
    error_message   TEXT,
    context_snapshot TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_heartbeat_runs_session ON heartbeat_runs(session_id);
CREATE INDEX IF NOT EXISTS idx_heartbeat_runs_status ON heartbeat_runs(status);
CREATE INDEX IF NOT EXISTS idx_heartbeat_runs_heartbeat ON heartbeat_runs(heartbeat_at);

-- ============================================================================
-- Wakeup requests (serialized session triggers with coalescing)
-- ============================================================================

CREATE TABLE IF NOT EXISTS wakeup_requests (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL REFERENCES workflow_sessions(id) ON DELETE CASCADE,
    reason          TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','processing','completed','coalesced','failed','deferred')),
    coalesced_count INTEGER DEFAULT 0,
    payload_json    TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    processed_at    TEXT
);
CREATE INDEX IF NOT EXISTS idx_wakeup_requests_session ON wakeup_requests(session_id);
CREATE INDEX IF NOT EXISTS idx_wakeup_requests_status ON wakeup_requests(status);

-- ============================================================================
-- Cost events (per-execution cost tracking)
-- ============================================================================

CREATE TABLE IF NOT EXISTS cost_events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    TEXT NOT NULL REFERENCES workflow_sessions(id) ON DELETE CASCADE,
    run_id        TEXT,
    node_id       TEXT,
    adapter_name  TEXT,
    model_name    TEXT,
    input_tokens  INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cost_usd      REAL DEFAULT 0.0,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_cost_events_session ON cost_events(session_id);
CREATE INDEX IF NOT EXISTS idx_cost_events_run ON cost_events(run_id);
CREATE INDEX IF NOT EXISTS idx_cost_events_created ON cost_events(created_at);

-- ============================================================================
-- Task sessions (adapter session persistence)
-- ============================================================================

CREATE TABLE IF NOT EXISTS task_sessions (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id           TEXT NOT NULL REFERENCES workflow_sessions(id) ON DELETE CASCADE,
    node_id              TEXT NOT NULL,
    task_key             TEXT NOT NULL,
    adapter_name         TEXT NOT NULL,
    adapter_session_id   TEXT,
    adapter_state_json   TEXT,
    last_run_id          TEXT,
    created_at           TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at           TEXT,
    UNIQUE(session_id, task_key)
);
CREATE INDEX IF NOT EXISTS idx_task_sessions_session ON task_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_task_sessions_task_key ON task_sessions(session_id, task_key);

-- ============================================================================
-- Environment Variables (per-project settings)
-- ============================================================================

CREATE TABLE IF NOT EXISTS env_vars (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    is_secret  INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

def get_schema_sql() -> str:
    """Return the full schema creation SQL."""
    return _SCHEMA_SQL


def get_rebuild_sql() -> str:
    """Return SQL that drops all tables and recreates from the full schema.

    Used when an existing DB is outdated. The full schema in _SCHEMA_SQL is
    the single source of truth — no incremental migrations needed.
    """
    return _DROP_ALL_SQL + "\n" + _SCHEMA_SQL



# Drop all tables in reverse dependency order for clean rebuild.
# Includes legacy table names for backwards compat with older DBs.
_DROP_ALL_SQL = """
PRAGMA foreign_keys=OFF;
-- FTS virtual tables
DROP TABLE IF EXISTS incidents_fts;
DROP TABLE IF EXISTS chunks_fts;
DROP TABLE IF EXISTS artifacts_fts;
DROP TABLE IF EXISTS chain_signals_fts;
-- Triggers
DROP TRIGGER IF EXISTS incidents_ai;
DROP TRIGGER IF EXISTS incidents_ad;
DROP TRIGGER IF EXISTS incidents_au;
DROP TRIGGER IF EXISTS chunks_ai;
DROP TRIGGER IF EXISTS chunks_ad;
DROP TRIGGER IF EXISTS chunks_au;
DROP TRIGGER IF EXISTS artifacts_ai;
DROP TRIGGER IF EXISTS artifacts_ad;
DROP TRIGGER IF EXISTS artifacts_au;
DROP TRIGGER IF EXISTS chain_signals_ai;
DROP TRIGGER IF EXISTS chain_signals_ad;
DROP TRIGGER IF EXISTS chain_signals_au;
-- Leaf tables (no dependents)
DROP TABLE IF EXISTS env_vars;
DROP TABLE IF EXISTS wakeup_requests;
DROP TABLE IF EXISTS cost_events;
DROP TABLE IF EXISTS task_sessions;
DROP TABLE IF EXISTS heartbeat_runs;
DROP TABLE IF EXISTS quality_scores;
DROP TABLE IF EXISTS chain_signals;
DROP TABLE IF EXISTS execution_chain_edges;
DROP TABLE IF EXISTS execution_chain_nodes;
DROP TABLE IF EXISTS execution_chains;
DROP TABLE IF EXISTS session_report_jobs;
DROP TABLE IF EXISTS autonomy_outcomes;
DROP TABLE IF EXISTS autonomy_profiles;
DROP TABLE IF EXISTS agent_metrics;
DROP TABLE IF EXISTS artifact_summaries;
DROP TABLE IF EXISTS artifact_chunks;
DROP TABLE IF EXISTS knowledge_manifest;
DROP TABLE IF EXISTS id_sequences;
DROP TABLE IF EXISTS incidents;
DROP TABLE IF EXISTS artifacts;
DROP TABLE IF EXISTS chunks;
DROP TABLE IF EXISTS documents;
DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS loop_states;
DROP TABLE IF EXISTS node_instances;
DROP TABLE IF EXISTS workflow_sessions;
DROP TABLE IF EXISTS workflow_snapshots;
DROP TABLE IF EXISTS config;
DROP TABLE IF EXISTS notes;
DROP TABLE IF EXISTS state_transitions;
DROP TABLE IF EXISTS feature_dependencies;
DROP TABLE IF EXISTS features;
DROP TABLE IF EXISTS milestone_dependencies;
DROP TABLE IF EXISTS milestones;
DROP TABLE IF EXISTS epics;
DROP TABLE IF EXISTS roadmaps;
DROP TABLE IF EXISTS schema_version;
PRAGMA foreign_keys=ON;
"""
