import os

MAX_CHARS = 10_000
MAX_ROUNDS = 10
SECRET_MARKERS = ("KEY", "TOKEN", "SECRET", "PASSWORD")


def clean_env() -> dict[str, str]:
    """Environment for child processes, without anything that looks like a secret."""
    return {
        name: value
        for name, value in os.environ.items()
        if not any(marker in name.upper() for marker in SECRET_MARKERS)
    }