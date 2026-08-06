"""
Environment configuration.

Real test suites never hardcode a URL. They run the exact same tests
against dev / staging / prod (or in this case, just demonstrate the
pattern against SauceDemo's own standard/problem-user variants) by
switching one environment variable: TEST_ENV.

Usage:
    from config.environments import get_config
    cfg = get_config()          # reads TEST_ENV from .env, defaults to "standard"
    cfg.base_url
    cfg.username
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class EnvConfig:
    name: str
    base_url: str
    username: str
    password: str
    default_timeout_ms: int = 10_000


_ENVIRONMENTS = {
    # SauceDemo exposes several demo "user types" that behave differently —
    # a nice stand-in for dev/staging/prod having different data/behavior.
    "standard": EnvConfig(
        name="standard",
        base_url="https://www.saucedemo.com",
        username="standard_user",
        password="secret_sauce",
    ),
    "locked_out": EnvConfig(
        name="locked_out",
        base_url="https://www.saucedemo.com",
        username="locked_out_user",
        password="secret_sauce",
    ),
    "problem_user": EnvConfig(
        name="problem_user",
        base_url="https://www.saucedemo.com",
        username="problem_user",
        password="secret_sauce",
    ),
    "performance_glitch": EnvConfig(
        name="performance_glitch",
        base_url="https://www.saucedemo.com",
        username="performance_glitch_user",
        password="secret_sauce",
        default_timeout_ms=20_000,  # this user is deliberately slow
    ),
}


def get_config(env_name: str | None = None) -> EnvConfig:
    """Resolve which environment config to use, defaulting to TEST_ENV in .env."""
    name = env_name or os.getenv("TEST_ENV", "standard")
    if name not in _ENVIRONMENTS:
        raise ValueError(
            f"Unknown TEST_ENV '{name}'. Valid options: {list(_ENVIRONMENTS.keys())}"
        )
    return _ENVIRONMENTS[name]
