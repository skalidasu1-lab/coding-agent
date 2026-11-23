import os

MAX_CHARS = 10_000
MAX_ROUNDS = 20
SECRET_MARKERS = ("KEY", "TOKEN", "SECRET", "PASSWORD")


def clean_env() -> dict[str, str]:
    """Environment for child processes, without anything that looks like a secret."""
    return {
        name: value
        for name, value in os.environ.items()
        if not any(marker in name.upper() for marker in SECRET_MARKERS)
    }


def make_client():
    from openai import OpenAI

    base_url = os.environ.get("LLM_BASE_URL", "https://openrouter.ai/api/v1")
    api_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
    if api_key is None:
        if "openrouter.ai" in base_url:
            raise RuntimeError("OPENROUTER_API_KEY not found. Check your .env file.")
        api_key = "not-needed"  # local servers ignore the key
    return OpenAI(base_url=base_url, api_key=api_key)


def apply_child_limits():
    """Runs in the child process just before it starts (POSIX only)."""
    import resource

    resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
    resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 * 1024, 10 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))


def child_kwargs() -> dict:
    """Extra subprocess.run arguments that cap what a child process can use."""
    if os.name == "posix":
        return {"preexec_fn": apply_child_limits}
    return {}