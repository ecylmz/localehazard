"""Role: machine text (keys written to a sorted index later searched bytewise)."""
import locale


def sort_index_keys(keys: list[str]) -> list[str]:
    """Sort index keys."""
    return sorted(keys, key=locale.strxfrm)
