from typing import Any, Protocol

from decision_center.models import AgentType, Task


class AgentExecutor(Protocol):
    def __call__(self, task: Task) -> dict[str, Any]: ...


class UnsupportedAgentError(RuntimeError):
    """Agent type has no active execution adapter."""


def _codex_executor(task: Task) -> dict[str, Any]:
    return {"agent_type": AgentType.CODEX, "summary": f"Completed task: {task.title}"}


def _qwen_executor(task: Task) -> dict[str, Any]:
    return {"agent_type": AgentType.QWEN, "summary": f"Completed task: {task.title}"}


def _deepseek_executor(task: Task) -> dict[str, Any]:
    return {"agent_type": AgentType.DEEPSEEK, "summary": f"Completed task: {task.title}"}


class WorkerManager:
    """Registry for active and reserved agent execution adapters."""

    reserved_types = frozenset({AgentType.CLAUDE, AgentType.GEMINI})

    def __init__(self, executors: dict[AgentType, AgentExecutor] | None = None) -> None:
        self._executors: dict[AgentType, AgentExecutor] = executors or {
            AgentType.CODEX: _codex_executor,
            AgentType.QWEN: _qwen_executor,
            AgentType.DEEPSEEK: _deepseek_executor,
        }

    @property
    def supported_types(self) -> frozenset[AgentType]:
        return frozenset(self._executors)

    def execute(self, agent_type: AgentType, task: Task) -> dict[str, Any]:
        executor = self._executors.get(agent_type)
        if executor is None:
            raise UnsupportedAgentError(f"Agent type {agent_type} is reserved or unsupported")
        return executor(task)
