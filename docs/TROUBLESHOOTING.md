# Closed Beta Troubleshooting

| Symptom | Check | Recovery |
|---|---|---|
| Login rejected | user status, invitation expiry, clock | resend invite or reactivate access |
| Research queued | system health, worker, Redis | restore dependency; avoid duplicate launches |
| Provider unavailable | registry health and credentials | allow Router failover or disable provider |
| Report missing | execution and extraction status | retry failed execution with correlation ID |
| Notification missing | outbox and channel preferences | retry delivery; retain canonical in-app record |
| Export fails | report version and worker logs | retry after report finalization |

For infrastructure incidents follow [RUNBOOK.md](RUNBOOK.md) and
[INCIDENT_RESPONSE.md](INCIDENT_RESPONSE.md). Do not repair production data with
direct SQL outside an approved recovery procedure.
