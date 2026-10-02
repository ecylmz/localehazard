"""Role: machine text (configuration keyword)."""


def config_key(keyword: str) -> str:
    """Return the canonical key."""
    return keyword.lower()
