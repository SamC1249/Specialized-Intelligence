"""Central allow/block lists for `scripts/policy_lint.py`.

Kept as a plain module (not YAML/TOML) so the linter has zero runtime
dependencies and mypy can type-check it. Any new source or exception must
edit this file and cite a reason in the accompanying `docs/plan-*.md`.
"""

from __future__ import annotations

BLOCKED_HOSTS: frozenset[str] = frozenset(
    {
        "www.youtube.com/watch",
        "youtu.be/",
        "www.tiktok.com/",
        "vimeo.com/",
        "dailymotion.com/",
        "facebook.com/watch",
        "www.instagram.com/reel",
        "www.twitch.tv/videos",
    }
)

ALLOWED_HOSTS: frozenset[str] = frozenset(
    {
        "commons.wikimedia.org",
        "upload.wikimedia.org",
        "archive.org",
        "example.peertube.test",
        "example.org",
        "webdatacommons.org",
        "commoncrawl.org",
        "index.commoncrawl.org",
        "framatube.org",
    }
)

REDISTRIBUTABLE_LICENSES: frozenset[str] = frozenset(
    {"CC0", "CC-BY", "CC-BY-SA", "PUBLIC_DOMAIN", "OTHER_FREE"}
)

POLICY_LINT_EXEMPT_PATHS: frozenset[str] = frozenset(
    {
        "docs/",
        "scripts/policy_allowlist.py",
        "scripts/policy_lint.py",
        "tests/",
        "AGENTS.md",
        "README.md",
        "plan.md",
        "db_structured.md",
    }
)
