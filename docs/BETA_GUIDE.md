# Closed Beta Guide

1. Sign in with an invited account.
2. Open **Getting Started** and create or select an organization.
3. Run the prefilled Skinjestique research and verify its final report.
4. Verify notification, view-only sharing and export workflows.
5. Submit feedback from the application with the related project or research.

Prepare demo data idempotently:

```bash
export BETA_DEMO_PASSWORD='<temporary password of at least 12 characters>'
python scripts/seed_closed_beta.py
```

The seed creates Demo Organization, owner/analyst/viewer accounts, three projects
and a Skinjestique sample research. Rotate or disable demo credentials before
exposing the environment to untrusted users.

Use invitations rather than shared accounts. Review Product Analytics, provider
cost and operations alerts each business day. Record defects in Feedback Center.
