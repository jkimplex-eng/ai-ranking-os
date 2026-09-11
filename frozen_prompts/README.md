# Frozen Prompt Sets

Versioned and immutable prompt sets for reproducible AI visibility measurements. Query fan-out is
deterministic: the same version and variables produce the same ordered queries and fingerprint.
Activating a version deactivates older versions with the same code.

API:

- `POST /geo/prompt-sets`
- `GET /geo/prompt-sets`
- `GET /geo/prompt-sets/{prompt_set_id}`
- `POST /geo/prompt-sets/{prompt_set_id}/activate`
- `POST /geo/prompt-sets/{prompt_set_id}/fan-out`

