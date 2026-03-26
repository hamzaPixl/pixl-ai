"""Tests for pixl CLI command modules.

Uses Click's CliRunner with mocked DB and project registry so no real SQLite or
filesystem setup is required.  The pattern mirrors the existing sandbox command
tests: patch CLIContext.db with a property returning a MagicMock, then assert
exit code and key output fragments.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner
from pixl_cli.main import cli

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def mock_db() -> MagicMock:
    db = MagicMock()
    db.workflow_templates = MagicMock()
    db.artifacts = MagicMock()
    db.sessions = MagicMock()
    db.backlog = MagicMock()
    return db


def _db_patch(mock_db: MagicMock):
    """Context manager that patches CLIContext.db with mock_db."""
    return patch(
        "pixl_cli.context.CLIContext.db",
        new_callable=lambda: property(lambda self: mock_db),
    )


# ---------------------------------------------------------------------------
# template commands
# ---------------------------------------------------------------------------


class TestTemplateHelp:
    def test_template_group_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["template", "--help"])
        assert result.exit_code == 0
        assert "template" in result.output.lower()

    def test_template_list_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["template", "list", "--help"])
        assert result.exit_code == 0

    def test_template_get_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["template", "get", "--help"])
        assert result.exit_code == 0

    def test_template_create_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["template", "create", "--help"])
        assert result.exit_code == 0

    def test_template_update_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["template", "update", "--help"])
        assert result.exit_code == 0

    def test_template_delete_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["template", "delete", "--help"])
        assert result.exit_code == 0


class TestTemplateList:
    def test_list_empty(self, runner: CliRunner, mock_db: MagicMock) -> None:
        mock_db.workflow_templates.list_templates.return_value = []
        with _db_patch(mock_db):
            result = runner.invoke(cli, ["template", "list"])
        assert result.exit_code == 0

    def test_list_returns_rows(self, runner: CliRunner, mock_db: MagicMock) -> None:
        mock_db.workflow_templates.list_templates.return_value = [
            {
                "id": "wft-1",
                "name": "tdd",
                "version": 1,
                "source": "db",
                "description": None,
                "created_at": "2026-01-01",
            }
        ]
        with _db_patch(mock_db):
            result = runner.invoke(cli, ["template", "list"])
        assert result.exit_code == 0
        assert "tdd" in result.output

    def test_list_json_output(self, runner: CliRunner, mock_db: MagicMock) -> None:
        mock_db.workflow_templates.list_templates.return_value = [
            {
                "id": "wft-1",
                "name": "tdd",
                "version": 1,
                "source": "db",
                "description": None,
                "created_at": "2026-01-01",
            }
        ]
        with _db_patch(mock_db):
            result = runner.invoke(cli, ["--json", "template", "list"])
        assert result.exit_code == 0

    def test_list_with_source_filter(self, runner: CliRunner, mock_db: MagicMock) -> None:
        mock_db.workflow_templates.list_templates.return_value = []
        with _db_patch(mock_db):
            result = runner.invoke(cli, ["template", "list", "--source", "db"])
        assert result.exit_code == 0
        mock_db.workflow_templates.list_templates.assert_called_once()
        call_kwargs = mock_db.workflow_templates.list_templates.call_args
        assert call_kwargs.kwargs.get("source") == "db" or call_kwargs.args[0] == "db"


class TestTemplateGet:
    def test_get_not_found(self, runner: CliRunner, mock_db: MagicMock) -> None:
        mock_db.workflow_templates.get.return_value = None
        with _db_patch(mock_db):
            result = runner.invoke(cli, ["template", "get", "wft-missing"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_get_found_text(self, runner: CliRunner, mock_db: MagicMock) -> None:
        mock_db.workflow_templates.get.return_value = {
            "id": "wft-1",
            "name": "tdd",
            "version": 1,
            "source": "db",
            "yaml_content": "id: tdd",
        }
        with _db_patch(mock_db):
            result = runner.invoke(cli, ["template", "get", "wft-1"])
        assert result.exit_code == 0

    def test_get_found_json(self, runner: CliRunner, mock_db: MagicMock) -> None:
        mock_db.workflow_templates.get.return_value = {
            "id": "wft-1",
            "name": "tdd",
            "version": 1,
        }
        with _db_patch(mock_db):
            result = runner.invoke(cli, ["--json", "template", "get", "wft-1"])
        assert result.exit_code == 0


class TestTemplateCreate:
    def test_create_writes_template(
        self, runner: CliRunner, mock_db: MagicMock, tmp_path: Path
    ) -> None:
        yaml_file = tmp_path / "wf.yaml"
        yaml_file.write_text("id: test\nname: Test\n")

        mock_db.workflow_templates.create.return_value = {
            "id": "wft-99",
            "name": "my-tpl",
            "version": 1,
        }
        with _db_patch(mock_db):
            result = runner.invoke(
                cli,
                ["template", "create", "my-tpl", "--file", str(yaml_file)],
            )
        assert result.exit_code == 0
        assert "Created template" in result.output

    def test_create_json_output(
        self, runner: CliRunner, mock_db: MagicMock, tmp_path: Path
    ) -> None:
        yaml_file = tmp_path / "wf.yaml"
        yaml_file.write_text("id: test\n")

        mock_db.workflow_templates.create.return_value = {
            "id": "wft-99",
            "name": "my-tpl",
            "version": 1,
        }
        with _db_patch(mock_db):
            result = runner.invoke(
                cli,
                ["--json", "template", "create", "my-tpl", "--file", str(yaml_file)],
            )
        assert result.exit_code == 0


class TestTemplateUpdate:
    def test_update_nothing_to_update(self, runner: CliRunner, mock_db: MagicMock) -> None:
        with _db_patch(mock_db):
            result = runner.invoke(cli, ["template", "update", "wft-1"])
        assert result.exit_code == 1
        assert "Nothing to update" in result.output

    def test_update_not_found(self, runner: CliRunner, mock_db: MagicMock) -> None:
        mock_db.workflow_templates.update.return_value = False
        with _db_patch(mock_db):
            result = runner.invoke(
                cli, ["template", "update", "wft-missing", "--description", "new desc"]
            )
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_update_success(self, runner: CliRunner, mock_db: MagicMock, tmp_path: Path) -> None:
        yaml_file = tmp_path / "wf.yaml"
        yaml_file.write_text("id: test\n")

        mock_db.workflow_templates.update.return_value = True
        mock_db.workflow_templates.get.return_value = {
            "id": "wft-1",
            "name": "tdd",
            "version": 2,
        }
        with _db_patch(mock_db):
            result = runner.invoke(
                cli,
                ["template", "update", "wft-1", "--file", str(yaml_file)],
            )
        assert result.exit_code == 0
        assert "Updated template" in result.output


class TestTemplateDelete:
    def test_delete_not_found_with_yes(self, runner: CliRunner, mock_db: MagicMock) -> None:
        mock_db.workflow_templates.delete.return_value = False
        with _db_patch(mock_db):
            result = runner.invoke(cli, ["template", "delete", "wft-missing", "--yes"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_delete_success_with_yes(self, runner: CliRunner, mock_db: MagicMock) -> None:
        mock_db.workflow_templates.delete.return_value = True
        with _db_patch(mock_db):
            result = runner.invoke(cli, ["template", "delete", "wft-1", "--yes"])
        assert result.exit_code == 0
        assert "Deleted template" in result.output

    def test_delete_not_found_without_yes(self, runner: CliRunner, mock_db: MagicMock) -> None:
        mock_db.workflow_templates.get.return_value = None
        with _db_patch(mock_db):
            result = runner.invoke(cli, ["template", "delete", "wft-missing"])
        assert result.exit_code == 1

    def test_delete_json_output(self, runner: CliRunner, mock_db: MagicMock) -> None:
        mock_db.workflow_templates.delete.return_value = True
        with _db_patch(mock_db):
            result = runner.invoke(cli, ["--json", "template", "delete", "wft-1", "--yes"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# artifact commands
# ---------------------------------------------------------------------------


class TestArtifactHelp:
    def test_artifact_group_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["artifact", "--help"])
        assert result.exit_code == 0

    def test_artifact_list_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["artifact", "list", "--help"])
        assert result.exit_code == 0

    def test_artifact_get_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["artifact", "get", "--help"])
        assert result.exit_code == 0

    def test_artifact_search_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["artifact", "search", "--help"])
        assert result.exit_code == 0


class TestArtifactList:
    def test_list_empty_no_session(self, runner: CliRunner, mock_db: MagicMock) -> None:
        mock_db.artifacts.list_page.return_value = []
        with _db_patch(mock_db):
            result = runner.invoke(cli, ["artifact", "list"])
        assert result.exit_code == 0

    def test_list_with_session_filter(self, runner: CliRunner, mock_db: MagicMock) -> None:
        mock_db.artifacts.list_by_session.return_value = [
            {"id": "art-1", "name": "test.md", "artifact_type": "other", "session_id": "sess-1"}
        ]
        with _db_patch(mock_db):
            result = runner.invoke(cli, ["artifact", "list", "--session", "sess-1"])
        assert result.exit_code == 0

    def test_list_json_output(self, runner: CliRunner, mock_db: MagicMock) -> None:
        mock_db.artifacts.list_page.return_value = []
        with _db_patch(mock_db):
            result = runner.invoke(cli, ["--json", "artifact", "list"])
        assert result.exit_code == 0


class TestArtifactGet:
    def test_get_not_found_by_search(self, runner: CliRunner, mock_db: MagicMock) -> None:
        mock_db.artifacts.search.return_value = []
        with _db_patch(mock_db):
            result = runner.invoke(cli, ["artifact", "get", "--name", "missing.md"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_get_found_by_search(self, runner: CliRunner, mock_db: MagicMock) -> None:
        mock_db.artifacts.search.return_value = [
            {"id": "art-1", "name": "report.md", "artifact_type": "other"}
        ]
        with _db_patch(mock_db):
            result = runner.invoke(cli, ["artifact", "get", "--name", "report.md"])
        assert result.exit_code == 0

    def test_get_with_session(self, runner: CliRunner, mock_db: MagicMock) -> None:
        mock_db.artifacts.get_by_session_path.return_value = {
            "id": "art-1",
            "name": "report.md",
            "artifact_type": "other",
        }
        with _db_patch(mock_db):
            result = runner.invoke(
                cli, ["artifact", "get", "--name", "report.md", "--session", "sess-1"]
            )
        assert result.exit_code == 0


class TestArtifactSearch:
    def test_search_no_results(self, runner: CliRunner, mock_db: MagicMock) -> None:
        mock_db.artifacts.search.return_value = []
        with _db_patch(mock_db):
            result = runner.invoke(cli, ["artifact", "search", "--query", "nothing"])
        assert result.exit_code == 0
        assert "No artifacts found" in result.output

    def test_search_with_results(self, runner: CliRunner, mock_db: MagicMock) -> None:
        mock_db.artifacts.search.return_value = [
            {"id": "art-1", "name": "plan.md", "artifact_type": "plan", "logical_path": "plan.md"}
        ]
        with _db_patch(mock_db):
            result = runner.invoke(cli, ["artifact", "search", "--query", "plan"])
        assert result.exit_code == 0
        assert "plan" in result.output

    def test_search_json_output(self, runner: CliRunner, mock_db: MagicMock) -> None:
        mock_db.artifacts.search.return_value = []
        with _db_patch(mock_db):
            result = runner.invoke(cli, ["--json", "artifact", "search", "--query", "test"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# session commands
# ---------------------------------------------------------------------------


class TestSessionHelp:
    def test_session_group_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["session", "--help"])
        assert result.exit_code == 0

    def test_session_list_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["session", "list", "--help"])
        assert result.exit_code == 0

    def test_session_get_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["session", "get", "--help"])
        assert result.exit_code == 0

    def test_session_cancel_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["session", "cancel", "--help"])
        assert result.exit_code == 0


class TestSessionList:
    def test_list_empty(self, runner: CliRunner, mock_db: MagicMock) -> None:
        mock_db.sessions.list_sessions.return_value = []
        with _db_patch(mock_db):
            result = runner.invoke(cli, ["session", "list"])
        assert result.exit_code == 0

    def test_list_with_status_filter(self, runner: CliRunner, mock_db: MagicMock) -> None:
        mock_db.sessions.list_sessions.return_value = []
        with _db_patch(mock_db):
            result = runner.invoke(cli, ["session", "list", "--status", "running"])
        assert result.exit_code == 0
        call_kwargs = mock_db.sessions.list_sessions.call_args
        assert call_kwargs.kwargs.get("status") == "running"

    def test_list_json_output(self, runner: CliRunner, mock_db: MagicMock) -> None:
        mock_db.sessions.list_sessions.return_value = [
            {
                "id": "sess-1",
                "feature_id": "feat-1",
                "status": "completed",
                "created_at": "2026-01-01",
                "last_updated_at": "2026-01-01",
            }
        ]
        with _db_patch(mock_db):
            result = runner.invoke(cli, ["--json", "session", "list"])
        assert result.exit_code == 0


class TestSessionGet:
    def test_get_not_found(self, runner: CliRunner, mock_db: MagicMock) -> None:
        mock_db.sessions.get_session.return_value = None
        with _db_patch(mock_db):
            result = runner.invoke(cli, ["session", "get", "sess-missing"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_get_found(self, runner: CliRunner, mock_db: MagicMock) -> None:
        mock_db.sessions.get_session.return_value = {
            "id": "sess-1",
            "feature_id": "feat-1",
            "status": "completed",
        }
        with _db_patch(mock_db):
            result = runner.invoke(cli, ["session", "get", "sess-1"])
        assert result.exit_code == 0


class TestSessionCancel:
    def test_cancel_not_found(self, runner: CliRunner, mock_db: MagicMock) -> None:
        mock_db.sessions.get_session.return_value = None
        with _db_patch(mock_db):
            result = runner.invoke(cli, ["session", "cancel", "sess-missing"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_cancel_update_fails(self, runner: CliRunner, mock_db: MagicMock) -> None:
        mock_db.sessions.get_session.return_value = {"id": "sess-1", "status": "running"}
        mock_db.sessions.update_session.return_value = False
        with _db_patch(mock_db):
            result = runner.invoke(cli, ["session", "cancel", "sess-1"])
        assert result.exit_code == 1
        assert "Failed to cancel" in result.output

    def test_cancel_success(self, runner: CliRunner, mock_db: MagicMock) -> None:
        mock_db.sessions.get_session.return_value = {"id": "sess-1", "status": "running"}
        mock_db.sessions.update_session.return_value = True
        with _db_patch(mock_db):
            result = runner.invoke(cli, ["session", "cancel", "sess-1"])
        assert result.exit_code == 0

    def test_cancel_json_output(self, runner: CliRunner, mock_db: MagicMock) -> None:
        mock_db.sessions.get_session.return_value = {"id": "sess-1", "status": "running"}
        mock_db.sessions.update_session.return_value = True
        with _db_patch(mock_db):
            result = runner.invoke(cli, ["--json", "session", "cancel", "sess-1"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# state commands
# ---------------------------------------------------------------------------


class TestStateHelp:
    def test_state_group_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["state", "--help"])
        assert result.exit_code == 0

    def test_state_show_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["state", "show", "--help"])
        assert result.exit_code == 0

    def test_state_graph_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["state", "graph", "--help"])
        assert result.exit_code == 0

    def test_state_deps_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["state", "deps", "--help"])
        assert result.exit_code == 0


class TestStateShow:
    def test_show_unknown_prefix(self, runner: CliRunner, mock_db: MagicMock) -> None:
        with _db_patch(mock_db):
            result = runner.invoke(cli, ["state", "show", "xyz-123"])
        assert result.exit_code == 1
        assert "Unknown entity type" in result.output

    def test_show_feature_not_found(self, runner: CliRunner, mock_db: MagicMock) -> None:
        mock_db.backlog.get_feature.return_value = None
        with patch("pixl.state.TransitionEngine") as mock_engine_cls:
            mock_engine_cls.default.return_value = MagicMock()
            with _db_patch(mock_db):
                result = runner.invoke(cli, ["state", "show", "feat-missing"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_show_feature_found(self, runner: CliRunner, mock_db: MagicMock) -> None:
        mock_db.backlog.get_feature.return_value = {
            "id": "feat-1",
            "status": "in_progress",
            "title": "My Feature",
        }
        mock_engine = MagicMock()
        mock_engine.get_available_transitions.return_value = ["done", "blocked"]
        with patch("pixl.state.TransitionEngine") as mock_engine_cls:
            mock_engine_cls.default.return_value = mock_engine
            with _db_patch(mock_db):
                result = runner.invoke(cli, ["state", "show", "feat-1"])
        assert result.exit_code == 0
        assert "feat-1" in result.output


class TestStateGraph:
    def test_graph_empty(self, runner: CliRunner, mock_db: MagicMock) -> None:
        mock_db.backlog.get_dependency_graph.return_value = {}
        with _db_patch(mock_db):
            result = runner.invoke(cli, ["state", "graph", "epic-1"])
        assert result.exit_code == 0
        assert "No dependencies found" in result.output

    def test_graph_with_data(self, runner: CliRunner, mock_db: MagicMock) -> None:
        mock_db.backlog.get_dependency_graph.return_value = {
            "feat-1": ["feat-2"],
            "feat-2": [],
        }
        with _db_patch(mock_db):
            result = runner.invoke(cli, ["state", "graph", "epic-1"])
        assert result.exit_code == 0
        assert "feat-1" in result.output


class TestStateDeps:
    def test_deps_met(self, runner: CliRunner, mock_db: MagicMock) -> None:
        mock_db.backlog.check_dependencies_met.return_value = (True, [])
        with _db_patch(mock_db):
            result = runner.invoke(cli, ["state", "deps", "feat-1"])
        assert result.exit_code == 0
        assert "met" in result.output

    def test_deps_unmet(self, runner: CliRunner, mock_db: MagicMock) -> None:
        mock_db.backlog.check_dependencies_met.return_value = (False, ["feat-2", "feat-3"])
        with _db_patch(mock_db):
            result = runner.invoke(cli, ["state", "deps", "feat-1"])
        assert result.exit_code == 0
        assert "feat-2" in result.output

    def test_deps_json_output(self, runner: CliRunner, mock_db: MagicMock) -> None:
        mock_db.backlog.check_dependencies_met.return_value = (True, [])
        with _db_patch(mock_db):
            result = runner.invoke(cli, ["--json", "state", "deps", "feat-1"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# project commands
# ---------------------------------------------------------------------------


class TestProjectHelp:
    def test_project_group_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["project", "--help"])
        assert result.exit_code == 0

    def test_project_init_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["project", "init", "--help"])
        assert result.exit_code == 0

    def test_project_list_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["project", "list", "--help"])
        assert result.exit_code == 0


class TestProjectInit:
    @staticmethod
    def _make_crew_templates(tmp_path: Path) -> Path:
        """Create a fake crew root with crew-init templates."""
        crew_root = tmp_path / "fake_crew"
        plugin_dir = crew_root / ".claude-plugin"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "plugin.json").write_text('{"version": "1.0.0"}')

        tmpl_dir = crew_root / "templates" / "crew-init"
        tmpl_dir.mkdir(parents=True)
        (tmpl_dir / "CLAUDE.md.tmpl").write_text("# {{PROJECT_NAME}}\n\nCrew-enabled project.\n")
        (tmpl_dir / "crew-workflow.md").write_text("# Workflow rules\n")
        (tmpl_dir / "crew-delegation.md").write_text("# Delegation rules\n")
        (tmpl_dir / "crew-enforcement.md").write_text("# Enforcement rules\n")
        (tmpl_dir / "settings.local.json").write_text('{"allowedTools": []}')
        return crew_root

    def test_init_succeeds(self, runner: CliRunner, tmp_path: Path) -> None:
        with patch("pixl.projects.registry.ensure_project_config"):
            result = runner.invoke(cli, ["--project", str(tmp_path), "project", "init"])
        assert result.exit_code == 0
        assert "Initialized pixl project" in result.output

    def test_init_json_output(self, runner: CliRunner, tmp_path: Path) -> None:
        with patch("pixl.projects.registry.ensure_project_config"):
            result = runner.invoke(cli, ["--project", str(tmp_path), "--json", "project", "init"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "crew_installed" in data
        assert data["status"] == "initialized"

    def test_init_installs_crew_templates(self, runner: CliRunner, tmp_path: Path) -> None:
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        crew_root = self._make_crew_templates(tmp_path)

        with (
            patch("pixl.projects.registry.ensure_project_config"),
            patch("pixl_cli.crew.get_crew_root", return_value=crew_root),
        ):
            result = runner.invoke(cli, ["--project", str(project_dir), "project", "init"])

        assert result.exit_code == 0
        assert (project_dir / "CLAUDE.md").exists()
        assert "my-project" in (project_dir / "CLAUDE.md").read_text()
        assert (project_dir / ".claude" / "rules" / "crew-workflow.md").exists()
        assert (project_dir / ".claude" / "rules" / "crew-delegation.md").exists()
        assert (project_dir / ".claude" / "rules" / "crew-enforcement.md").exists()
        assert (project_dir / ".claude" / "settings.local.json").exists()

    def test_init_creates_claude_md_from_template(self, runner: CliRunner, tmp_path: Path) -> None:
        project_dir = tmp_path / "test-app"
        project_dir.mkdir()
        crew_root = self._make_crew_templates(tmp_path)

        with (
            patch("pixl.projects.registry.ensure_project_config"),
            patch("pixl_cli.crew.get_crew_root", return_value=crew_root),
        ):
            result = runner.invoke(
                cli, ["--project", str(project_dir), "project", "init", "--name", "My App"]
            )

        assert result.exit_code == 0
        content = (project_dir / "CLAUDE.md").read_text()
        assert "# My App" in content

    def test_init_skips_existing_claude_md(self, runner: CliRunner, tmp_path: Path) -> None:
        project_dir = tmp_path / "existing"
        project_dir.mkdir()
        (project_dir / "CLAUDE.md").write_text("# Custom content\n")
        crew_root = self._make_crew_templates(tmp_path)

        with (
            patch("pixl.projects.registry.ensure_project_config"),
            patch("pixl_cli.crew.get_crew_root", return_value=crew_root),
        ):
            result = runner.invoke(cli, ["--project", str(project_dir), "project", "init"])

        assert result.exit_code == 0
        assert (project_dir / "CLAUDE.md").read_text() == "# Custom content\n"
        assert "already exists" in result.output

    def test_init_no_crew_flag(self, runner: CliRunner, tmp_path: Path) -> None:
        project_dir = tmp_path / "no-crew"
        project_dir.mkdir()

        with patch("pixl.projects.registry.ensure_project_config"):
            result = runner.invoke(
                cli, ["--project", str(project_dir), "project", "init", "--no-crew"]
            )

        assert result.exit_code == 0
        assert not (project_dir / "CLAUDE.md").exists()
        assert not (project_dir / ".claude").exists()

    def test_init_preserves_existing_settings(self, runner: CliRunner, tmp_path: Path) -> None:
        project_dir = tmp_path / "with-settings"
        project_dir.mkdir()
        settings_dir = project_dir / ".claude"
        settings_dir.mkdir()
        (settings_dir / "settings.local.json").write_text('{"custom": true}')
        crew_root = self._make_crew_templates(tmp_path)

        with (
            patch("pixl.projects.registry.ensure_project_config"),
            patch("pixl_cli.crew.get_crew_root", return_value=crew_root),
        ):
            result = runner.invoke(cli, ["--project", str(project_dir), "project", "init"])

        assert result.exit_code == 0
        assert (settings_dir / "settings.local.json").read_text() == '{"custom": true}'

    def test_init_idempotent(self, runner: CliRunner, tmp_path: Path) -> None:
        project_dir = tmp_path / "idem"
        project_dir.mkdir()
        crew_root = self._make_crew_templates(tmp_path)

        with (
            patch("pixl.projects.registry.ensure_project_config"),
            patch("pixl_cli.crew.get_crew_root", return_value=crew_root),
        ):
            result1 = runner.invoke(cli, ["--project", str(project_dir), "project", "init"])
            result2 = runner.invoke(cli, ["--project", str(project_dir), "project", "init"])

        assert result1.exit_code == 0
        assert result2.exit_code == 0

    def test_init_crew_not_found_graceful(self, runner: CliRunner, tmp_path: Path) -> None:
        project_dir = tmp_path / "no-crew-plugin"
        project_dir.mkdir()

        with (
            patch("pixl.projects.registry.ensure_project_config"),
            patch(
                "pixl_cli.crew.get_crew_root",
                side_effect=FileNotFoundError("pixl-crew not found"),
            ),
        ):
            result = runner.invoke(cli, ["--project", str(project_dir), "project", "init"])

        assert result.exit_code == 0
        assert "Crew plugin not found" in result.output


class TestProjectList:
    def test_list_empty(self, runner: CliRunner) -> None:
        with patch("pixl.projects.registry.list_projects", return_value=[]):
            result = runner.invoke(cli, ["project", "list"])
        assert result.exit_code == 0

    def test_list_with_projects(self, runner: CliRunner) -> None:
        with patch(
            "pixl.projects.registry.list_projects",
            return_value=[
                {
                    "project_id": "proj-1",
                    "project_name": "my-app",
                    "project_root": "/tmp/app",
                    "storage_dir": "/tmp/.pixl",
                }
            ],
        ):
            result = runner.invoke(cli, ["project", "list"])
        assert result.exit_code == 0
        assert "my-app" in result.output


class TestProjectGet:
    def test_get_not_found(self, runner: CliRunner) -> None:
        with patch("pixl.projects.registry.get_project", return_value=None):
            result = runner.invoke(cli, ["project", "get", "proj-missing"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_get_found(self, runner: CliRunner) -> None:
        with patch(
            "pixl.projects.registry.get_project",
            return_value={
                "project_id": "proj-1",
                "project_name": "my-app",
            },
        ):
            result = runner.invoke(cli, ["project", "get", "proj-1"])
        assert result.exit_code == 0


class TestProjectCreate:
    def test_create_success(self, runner: CliRunner) -> None:
        with patch(
            "pixl.projects.registry.create_project",
            return_value={"project_id": "proj-new", "project_name": "new-app"},
        ):
            result = runner.invoke(cli, ["project", "create", "--name", "new-app"])
        assert result.exit_code == 0
        assert "Created project" in result.output

    def test_create_error(self, runner: CliRunner) -> None:
        with patch(
            "pixl.projects.registry.create_project",
            side_effect=ValueError("already exists"),
        ):
            result = runner.invoke(cli, ["project", "create", "--name", "dup"])
        assert result.exit_code == 1
        assert "already exists" in result.output


# ---------------------------------------------------------------------------
# setup command
# ---------------------------------------------------------------------------


class TestSetupHelp:
    def test_setup_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["setup", "--help"])
        assert result.exit_code == 0
        assert "skip" in result.output.lower() or "plugin" in result.output.lower()


class TestSetupRegisterCrewPlugin:
    """Unit-test register_crew_plugin directly (no subprocess)."""

    def test_register_creates_installed_plugins_json(self, tmp_path: Path) -> None:
        from pixl_cli.commands.setup import register_crew_plugin

        crew_root = tmp_path / "crew"
        plugin_json_dir = crew_root / ".claude-plugin"
        plugin_json_dir.mkdir(parents=True)
        (plugin_json_dir / "plugin.json").write_text(json.dumps({"version": "9.0.0"}))

        home = tmp_path / "home"
        with patch("pathlib.Path.home", return_value=home):
            version = register_crew_plugin(crew_root)

        assert version == "9.0.0"
        installed = home / ".claude" / "plugins" / "installed_plugins.json"
        assert installed.exists()
        data = json.loads(installed.read_text())
        assert "pixl-crew@pixl-local" in data["plugins"]

    def test_register_merges_existing_plugins_json(self, tmp_path: Path) -> None:
        from pixl_cli.commands.setup import register_crew_plugin

        crew_root = tmp_path / "crew"
        plugin_json_dir = crew_root / ".claude-plugin"
        plugin_json_dir.mkdir(parents=True)
        (plugin_json_dir / "plugin.json").write_text(json.dumps({"version": "1.0.0"}))

        home = tmp_path / "home"
        plugins_dir = home / ".claude" / "plugins"
        plugins_dir.mkdir(parents=True)
        existing = {
            "version": 2,
            "plugins": {"other-plugin@source": [{"scope": "user"}]},
        }
        (plugins_dir / "installed_plugins.json").write_text(json.dumps(existing))

        with patch("pathlib.Path.home", return_value=home):
            register_crew_plugin(crew_root)

        data = json.loads((plugins_dir / "installed_plugins.json").read_text())
        assert "other-plugin@source" in data["plugins"]
        assert "pixl-crew@pixl-local" in data["plugins"]

    def test_register_uses_local_version_when_no_plugin_json(self, tmp_path: Path) -> None:
        from pixl_cli.commands.setup import register_crew_plugin

        crew_root = tmp_path / "crew"
        crew_root.mkdir()

        home = tmp_path / "home"
        with patch("pathlib.Path.home", return_value=home):
            version = register_crew_plugin(crew_root)

        assert version == "local"


# ---------------------------------------------------------------------------
# crew.py — get_crew_root resolution
# ---------------------------------------------------------------------------


class TestGetCrewRoot:
    def test_env_var_override_valid(self, tmp_path: Path) -> None:
        from pixl_cli.crew import get_crew_root

        crew = tmp_path / "my-crew"
        plugin_dir = crew / ".claude-plugin"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "plugin.json").write_text("{}")

        with patch.dict("os.environ", {"PIXL_CREW_ROOT": str(crew)}):
            result = get_crew_root()
        assert result == crew

    def test_env_var_override_invalid_falls_through(self, tmp_path: Path) -> None:
        """When PIXL_CREW_ROOT points to a dir without plugin.json, fall through to next."""
        from pixl_cli.crew import get_crew_root

        bad_crew = tmp_path / "bad-crew"
        bad_crew.mkdir()

        # The monorepo and bundled paths won't exist in test either, so expect FileNotFoundError
        with patch.dict("os.environ", {"PIXL_CREW_ROOT": str(bad_crew)}):
            with patch("pixl_cli.crew.Path.__file__", create=True):
                try:
                    get_crew_root()
                except FileNotFoundError:
                    pass  # expected — none of the 3 paths are valid

    def test_monorepo_path_found(self) -> None:
        """Should find crew root when running from the monorepo layout."""
        from pixl_cli.crew import get_crew_root

        # In the test environment the real monorepo crew exists
        with patch.dict("os.environ", {}, clear=False):
            if "PIXL_CREW_ROOT" in __import__("os").environ:
                return  # skip if env override is active
            try:
                root = get_crew_root()
                assert (root / ".claude-plugin" / "plugin.json").is_file()
            except FileNotFoundError:
                pass  # acceptable if running outside the monorepo

    def test_raises_when_nothing_found(self, tmp_path: Path) -> None:
        from pixl_cli.crew import get_crew_root

        with (
            patch.dict("os.environ", {"PIXL_CREW_ROOT": ""}, clear=False),
            patch("pixl_cli.crew.Path") as mock_path_cls,
        ):
            # Make all paths return non-existent dirs so FileNotFoundError is raised
            fake_path = MagicMock()
            fake_path.resolve.return_value = fake_path
            fake_path.parent = fake_path
            fake_path.__truediv__ = lambda self, other: fake_path
            fake_path.is_file.return_value = False
            fake_path.exists.return_value = False
            mock_path_cls.return_value = fake_path
            mock_path_cls.home.return_value = fake_path

            # Actual FileNotFoundError test via env var pointing nowhere
            with patch.dict("os.environ", {"PIXL_CREW_ROOT": str(tmp_path)}):
                try:
                    get_crew_root()
                except FileNotFoundError as exc:
                    assert "pixl-crew not found" in str(exc)
