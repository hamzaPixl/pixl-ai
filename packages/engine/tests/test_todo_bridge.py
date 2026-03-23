"""Tests for TodoWrite bridge — mirrors SDK todo updates to engine events."""

from pixl.agents.hooks.todo_bridge import create_todo_tracking_callback


class TestTodoTrackingCallback:
    def test_ignores_non_todowrite_tools(self):
        events: list[dict] = []
        cb = create_todo_tracking_callback(lambda **kw: events.append(kw))
        cb("Read", {"file_path": "/foo"})
        assert events == []

    def test_emits_event_for_todowrite(self):
        events: list[dict] = []
        cb = create_todo_tracking_callback(
            lambda **kw: events.append(kw),
            session_id="sess-1",
            node_id="node-1",
        )
        cb(
            "TodoWrite",
            {
                "todos": [
                    {
                        "content": "Write tests",
                        "status": "in_progress",
                        "activeForm": "Writing tests",
                    },
                ]
            },
        )
        assert len(events) == 1
        assert events[0]["event_type"] == "todo_update"
        assert events[0]["session_id"] == "sess-1"
        assert events[0]["node_id"] == "node-1"
        assert events[0]["payload"]["content"] == "Write tests"
        assert events[0]["payload"]["status"] == "in_progress"
        assert events[0]["payload"]["active_form"] == "Writing tests"

    def test_emits_multiple_todos(self):
        events: list[dict] = []
        cb = create_todo_tracking_callback(lambda **kw: events.append(kw))
        cb(
            "TodoWrite",
            {
                "todos": [
                    {"content": "Task 1", "status": "completed"},
                    {"content": "Task 2", "status": "pending"},
                ]
            },
        )
        assert len(events) == 2
        assert events[0]["payload"]["content"] == "Task 1"
        assert events[0]["payload"]["status"] == "completed"
        assert events[1]["payload"]["content"] == "Task 2"
        assert events[1]["payload"]["status"] == "pending"

    def test_handles_empty_todos(self):
        events: list[dict] = []
        cb = create_todo_tracking_callback(lambda **kw: events.append(kw))
        cb("TodoWrite", {"todos": []})
        assert events == []

    def test_handles_missing_fields(self):
        events: list[dict] = []
        cb = create_todo_tracking_callback(lambda **kw: events.append(kw))
        cb("TodoWrite", {"todos": [{}]})
        assert len(events) == 1
        assert events[0]["payload"]["status"] == "unknown"
        assert events[0]["payload"]["content"] == ""
        assert events[0]["payload"]["active_form"] is None

    def test_default_session_and_node_are_none(self):
        events: list[dict] = []
        cb = create_todo_tracking_callback(lambda **kw: events.append(kw))
        cb("TodoWrite", {"todos": [{"content": "task", "status": "pending"}]})
        assert events[0]["session_id"] is None
        assert events[0]["node_id"] is None

    def test_handles_missing_todos_key(self):
        events: list[dict] = []
        cb = create_todo_tracking_callback(lambda **kw: events.append(kw))
        cb("TodoWrite", {})
        assert events == []
