from project_monitoring.models import ProjectMonitor
from project_monitoring.ports import MonitorScheduleRequest, SchedulerPort
from project_monitoring.repository import MonitorRepository
from project_monitoring.schemas import ProjectMonitorRead, ProjectMonitorUpsert
from workspace.repository import ProjectRepository, WorkspaceRepository


class MonitorNotFoundError(LookupError):
    pass


class ProjectMonitoringService:
    def __init__(
        self,
        repository: MonitorRepository,
        scheduler: SchedulerPort,
        workspaces: WorkspaceRepository,
        projects: ProjectRepository,
    ) -> None:
        self.repository = repository
        self.scheduler = scheduler
        self.workspaces = workspaces
        self.projects = projects

    def _project(self, user_id: int, project_id: int):
        workspace = self.workspaces.get_or_create(user_id)
        return self.projects.get(workspace.id, project_id)

    @staticmethod
    def _read(monitor: ProjectMonitor) -> ProjectMonitorRead:
        return ProjectMonitorRead.model_validate(monitor, from_attributes=True)

    def get(self, user_id: int, project_id: int) -> ProjectMonitorRead:
        self._project(user_id, project_id)
        monitor = self.repository.get(project_id)
        if monitor is None:
            raise MonitorNotFoundError("Project monitoring is not configured")
        return self._read(monitor)

    def upsert(
        self, user_id: int, project_id: int, payload: ProjectMonitorUpsert
    ) -> ProjectMonitorRead:
        project = self._project(user_id, project_id)
        if not self.scheduler.validate_template(payload.template_research_id, project_id):
            raise ValueError("Template research must belong to the monitored project")
        request = MonitorScheduleRequest(
            name=f"{project.name} {payload.frequency.value.lower()} monitoring",
            research_id=payload.template_research_id,
            frequency=payload.frequency.value,
            models=[item.model_dump() for item in payload.models],
            query=payload.query,
            enabled=payload.enabled,
        )
        monitor = self.repository.get(project_id)
        result = (
            self.scheduler.update(monitor.schedule_id, request)
            if monitor
            else self.scheduler.create(request)
        )
        if monitor is None:
            monitor = ProjectMonitor(
                project_id=project_id,
                schedule_id=result.schedule_id,
                template_research_id=payload.template_research_id,
                frequency=payload.frequency.value,
                enabled=payload.enabled,
                query=payload.query,
                next_run_at=result.next_run_at,
            )
        else:
            monitor.template_research_id = payload.template_research_id
            monitor.frequency = payload.frequency.value
            monitor.enabled = payload.enabled
            monitor.query = payload.query
            monitor.next_run_at = result.next_run_at
        return self._read(self.repository.save(monitor))

    def delete(self, user_id: int, project_id: int) -> None:
        self._project(user_id, project_id)
        monitor = self.repository.get(project_id)
        if monitor is None:
            raise MonitorNotFoundError("Project monitoring is not configured")
        self.scheduler.delete(monitor.schedule_id)
        self.repository.delete(monitor)
