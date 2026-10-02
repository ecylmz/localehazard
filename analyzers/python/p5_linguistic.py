"""Role: linguistic text (names sorted for display to a Turkish user)."""
import locale


def sort_for_display(names: list[str]) -> list[str]:
    """Sort names for display."""
    return sorted(names, key=locale.strxfrm)
