# Database Restore

Restoration is destructive and requires a maintenance window.

1. Stop external traffic and run a fresh backup.
2. Verify the selected dump and target environment.
3. Run `deployment/production/scripts/restore.sh backups/<file>.dump`.
4. The script uses `pg_restore --clean --if-exists`, then upgrades to Alembic head.
5. Start/verify services and run the full production smoke test before restoring traffic.

Never restore a production dump into an environment with weaker access controls.
