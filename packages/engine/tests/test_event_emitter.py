"""Tests for the extracted EventEmitter collaborator.

Validates that EventEmitter correctly delegates to the store for event
persistence and invokes the event_callback for real-time streaming.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pixl.errors import StorageError
from pixl.execution.event_emitter import EventEmitter
from pixl.models.event import Event, EventType
from pixl.models.node_instance import NodeState


def _make_store() -> MagicMock:
    """Create a mock WorkflowSessionStore."""
    store = MagicMock()
    store.append_event = MagicMock()
    store.append_events_batch = MagicMock()
    store.commit_transition = MagicMock(
        return_value=Event.create(
            EventType.CHECKPOINT_SAVED,
            session_id="sess-1",
            node_id=None,
            data={},
        )
    )
    return store


def _make_event(session_id: str = "sess-1", node_id: str | None = "node-1") -> Event:
    return Event.create(EventType.TASK_STARTED, session_id=session_id, node_id=node_id, data={})


class TestEmitEvent:
    def test_persists_to_store(self) -> None:
        store = _make_store()
        emitter = EventEmitter(session_id="sess-1", store=store, event_callback=None)
        event = _make_event()

        emitter.emit_event(event)

        store.append_event.assert_called_once_with(event)

    def test_invokes_callback(self) -> None:
        store = _make_store()
        callback = MagicMock()
        emitter = EventEmitter(session_id="sess-1", store=store, event_callback=callback)
        event = _make_event()

        emitter.emit_event(event)

        callback.assert_called_once_with(event)

    def test_no_callback_does_not_raise(self) -> None:
        store = _make_store()
        emitter = EventEmitter(session_id="sess-1", store=store, event_callback=None)
        event = _make_event()

        emitter.emit_event(event)  # Should not raise

    def test_storage_error_emits_error_event_and_reraises(self) -> None:
        store = _make_store()
        store.append_event.side_effect = StorageError(
            "DB write failed", op="append_event", details="disk full"
        )
        emitter = EventEmitter(session_id="sess-1", store=store, event_callback=None)
        event = _make_event()

        with pytest.raises(StorageError):
            emitter.emit_event(event)


class TestEmitEventsBatch:
    def test_empty_batch_is_noop(self) -> None:
        store = _make_store()
        emitter = EventEmitter(session_id="sess-1", store=store, event_callback=None)

        emitter.emit_events_batch([])

        store.append_events_batch.assert_not_called()
        store.append_event.assert_not_called()

    def test_batch_persists_all_events(self) -> None:
        store = _make_store()
        callback = MagicMock()
        emitter = EventEmitter(session_id="sess-1", store=store, event_callback=callback)
        events = [_make_event(), _make_event()]

        emitter.emit_events_batch(events)

        store.append_events_batch.assert_called_once_with(events)
        assert callback.call_count == 2

    def test_batch_fallback_to_individual_on_failure(self) -> None:
        store = _make_store()
        store.append_events_batch.side_effect = Exception("batch failed")
        emitter = EventEmitter(session_id="sess-1", store=store, event_callback=None)
        events = [_make_event(), _make_event()]

        emitter.emit_events_batch(events)

        assert store.append_event.call_count == 2


class TestEmitErrorEvent:
    def test_creates_and_persists_error_event(self) -> None:
        store = _make_store()
        callback = MagicMock()
        emitter = EventEmitter(session_id="sess-1", store=store, event_callback=callback)
        from pixl.errors import PixlError

        error = PixlError(error_type="test_error", message="something broke")

        result = emitter.emit_error_event(error, node_id="node-1")

        assert result is not None
        assert result.type == EventType.ERROR
        store.append_event.assert_called_once()
        callback.assert_called_once()

    def test_storage_failure_logs_but_still_returns(self) -> None:
        store = _make_store()
        store.append_event.side_effect = StorageError(
            "DB write failed", op="append_event", details="disk full"
        )
        emitter = EventEmitter(session_id="sess-1", store=store, event_callback=None)
        from pixl.errors import PixlError

        error = PixlError(error_type="test_error", message="something broke")

        result = emitter.emit_error_event(error, node_id="node-1")

        # Should still return the event even if storage failed
        assert result is not None


class TestPersistEvent:
    def test_persists_and_broadcasts(self) -> None:
        store = _make_store()
        callback = MagicMock()
        incident_store = MagicMock()
        emitter = EventEmitter(
            session_id="sess-1",
            store=store,
            event_callback=callback,
            incident_store_getter=lambda: incident_store,
        )
        event = _make_event()

        emitter.persist_event(event)

        store.append_event.assert_called_once_with(event)
        callback.assert_called_once_with(event)

    def test_records_recovery_incidents(self) -> None:
        store = _make_store()
        incident_store = MagicMock()
        emitter = EventEmitter(
            session_id="sess-1",
            store=store,
            event_callback=None,
            incident_store_getter=lambda: incident_store,
        )
        event = Event.create(
            EventType.RECOVERY_SUCCEEDED, session_id="sess-1", node_id="node-1", data={}
        )

        emitter.persist_event(event)

        incident_store.record_from_event.assert_called_once_with(event)

    def test_does_not_record_non_recovery_incidents(self) -> None:
        store = _make_store()
        incident_store = MagicMock()
        emitter = EventEmitter(
            session_id="sess-1",
            store=store,
            event_callback=None,
            incident_store_getter=lambda: incident_store,
        )
        event = _make_event()

        emitter.persist_event(event)

        incident_store.record_from_event.assert_not_called()


class TestCommitTransition:
    def test_delegates_to_store(self) -> None:
        store = _make_store()
        callback = MagicMock()
        session = MagicMock()
        emitter = EventEmitter(session_id="sess-1", store=store, event_callback=callback)

        emitter.commit_transition(
            session=session,
            event_type=EventType.TASK_STARTED,
            node_id="node-1",
            payload={"key": "value"},
            from_state=None,
            to_state=NodeState.TASK_RUNNING,
        )

        store.commit_transition.assert_called_once_with(
            session,
            node_id="node-1",
            from_state=None,
            to_state=NodeState.TASK_RUNNING.value,
            event_type=EventType.TASK_STARTED,
            payload={"key": "value"},
        )
        callback.assert_called_once()

    def test_none_states_passed_as_none(self) -> None:
        store = _make_store()
        session = MagicMock()
        emitter = EventEmitter(session_id="sess-1", store=store, event_callback=None)

        emitter.commit_transition(
            session=session,
            event_type=EventType.CHECKPOINT_SAVED,
            node_id=None,
            payload={},
            from_state=None,
            to_state=None,
        )

        store.commit_transition.assert_called_once_with(
            session,
            node_id=None,
            from_state=None,
            to_state=None,
            event_type=EventType.CHECKPOINT_SAVED,
            payload={},
        )


class TestCheckpoint:
    def test_emits_checkpoint_event(self) -> None:
        store = _make_store()
        session = MagicMock()
        emitter = EventEmitter(session_id="sess-1", store=store, event_callback=None)

        emitter.checkpoint(session=session, reason="idle")

        store.commit_transition.assert_called_once()
        call_kwargs = store.commit_transition.call_args
        assert call_kwargs.kwargs["event_type"] == EventType.CHECKPOINT_SAVED
        assert call_kwargs.kwargs["payload"] == {"reason": "idle"}

    def test_checkpoint_without_reason(self) -> None:
        store = _make_store()
        session = MagicMock()
        emitter = EventEmitter(session_id="sess-1", store=store, event_callback=None)

        emitter.checkpoint(session=session, reason=None)

        call_kwargs = store.commit_transition.call_args
        assert call_kwargs.kwargs["payload"] == {}
