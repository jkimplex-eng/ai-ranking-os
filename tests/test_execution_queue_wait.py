from unittest.mock import Mock

import pytest

from execution_engine import service


def test_busy_agent_is_retried_without_holding_transaction(monkeypatch):
    db = Mock()
    manager = Mock()
    scheduled = (Mock(), Mock(), Mock())
    schedule = Mock(side_effect=[service.NoAgentAvailableError("busy"), scheduled])
    run = Mock(return_value="completed")
    sleep = Mock()
    monkeypatch.setattr(service, "schedule_task_execution", schedule)
    monkeypatch.setattr(service, "run_execution", run)
    monkeypatch.setattr(service.time, "monotonic", Mock(side_effect=[0, 0.1]))
    assert service.start_task_execution(
        db, 7, manager, retry_base_seconds=0, sleep=sleep, wait_for_agent_seconds=2
    ) == "completed"
    db.rollback.assert_called_once()
    sleep.assert_called_once_with(1.0)
    assert schedule.call_count == 2
    run.assert_called_once()


def test_agent_wait_has_a_deadline(monkeypatch):
    db = Mock()
    schedule = Mock(side_effect=service.NoAgentAvailableError("busy"))
    sleep = Mock()
    monkeypatch.setattr(service, "schedule_task_execution", schedule)
    monkeypatch.setattr(service.time, "monotonic", Mock(side_effect=[0, 1, 2]))
    with pytest.raises(service.NoAgentAvailableError):
        service.start_task_execution(
            db, 7, Mock(), retry_base_seconds=0, sleep=sleep, wait_for_agent_seconds=2
        )
    assert db.rollback.call_count == 2
    sleep.assert_called_once_with(1.0)
