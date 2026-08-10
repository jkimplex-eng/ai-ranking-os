# TASK-1119 — Settings Center

One orchestration screen now unifies Profile, Security, API Keys, LLM Providers,
Language, Region, Notifications, Theme, and Organization settings. It reuses the
public Authentication, Workspace, API Keys, Provider Registry, and Organization
APIs; no settings data or business logic is duplicated. User preferences persist
through the existing Workspace settings contract, so no migration is required.
