# Notification Center

Unified in-product notification inbox and delivery outbox. UI delivery is immediate; Email,
Telegram, and future Webhooks are persisted as pending deliveries behind the public
`DeliveryPort`, ready for workers and credentials without coupling the domain to provider SDKs.

The inbox supports read/unread state, read timestamps, archive, categories, priorities,
pagination, filters, and summary counters. Standard product events cover completed/failed
research, ready reports, organization invitations, role changes, processed feedback, and
system messages while preserving the existing operational events.
