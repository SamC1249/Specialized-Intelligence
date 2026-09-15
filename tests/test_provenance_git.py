from specint import provenance_git


def test_current_git_sha_returns_something():
    provenance_git.reset_cache()
    sha = provenance_git.current_git_sha()
    assert isinstance(sha, str)
    assert sha


def test_env_override_wins(monkeypatch):
    provenance_git.reset_cache()
    monkeypatch.setenv("SPECINT_EXTRACTOR_GIT", "deadbeef1234")
    assert provenance_git.current_git_sha() == "deadbeef1234"
    provenance_git.reset_cache()


def test_empty_env_override_falls_back(monkeypatch):
    provenance_git.reset_cache()
    monkeypatch.setenv("SPECINT_EXTRACTOR_GIT", "   ")
    assert provenance_git.current_git_sha() == provenance_git.FALLBACK
    provenance_git.reset_cache()
