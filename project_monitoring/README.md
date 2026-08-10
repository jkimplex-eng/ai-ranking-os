# Project Monitoring

Daily, weekly and monthly project monitoring backed exclusively by the existing Scheduler.
The module stores only the Project-to-Schedule association and communicates through
`SchedulerPort`; it does not create a queue or execute research itself.
