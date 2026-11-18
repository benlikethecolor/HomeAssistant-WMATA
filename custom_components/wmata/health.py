"""A small health summary without credentials, locations, or response bodies."""


def health_snapshot(coordinator):
    api = getattr(coordinator, "api", None)
    health = (
        api.health()
        if api is not None and callable(getattr(api, "health", None))
        else {}
    )
    if not isinstance(health, dict):
        health = {}
    metadata = getattr(coordinator, "metadata_status", None)
    if metadata is not None:
        health["metadata"] = dict(metadata)
    polling_ok = getattr(coordinator, "last_update_success", False)
    state = "healthy"
    if (
        not polling_ok
        or (metadata or {}).get("stale", False)
        or health.get("last_error_type")
        or any(s.get("stale") for s in health.get("feeds", {}).values())
    ):
        state = "degraded"
    if health.get("rate_limit_seconds", 0) > 0:
        state = "rate_limited"
    return {**health, "status": state, "polling_available": polling_ok}
