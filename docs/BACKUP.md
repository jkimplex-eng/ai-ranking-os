# Database Backup

`deployment/production/scripts/backup.sh` creates a timestamped PostgreSQL custom-format dump in
`deployment/production/backups`. `BACKUP_RETENTION_DAYS` controls local retention (14 by default).
Schedule daily execution with systemd timer or cron and copy encrypted backups to independent
storage. The database password is read from `.env` and is never embedded in the script.

Verify every backup is non-empty and perform a restore drill at least monthly. Backups are not
complete until an off-host copy has passed integrity and restore tests.
