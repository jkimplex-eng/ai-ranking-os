# Workspace

The workspace module is the authenticated product entry point. It aggregates recent research and
reports without duplicating scoring or research business logic. A workspace is provisioned lazily
for each authenticated user and is accessed through `GET/PATCH /workspace`.
