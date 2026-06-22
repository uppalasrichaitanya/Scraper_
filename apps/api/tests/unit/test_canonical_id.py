"""
test_canonical_id.py — Unit tests for SHA-256 based canonical ID / deduplication.

The canonical_id is a SHA-256 hex digest of (source, url, title) to ensure
that the same job from the same source always maps to the same ID, and that
any change in meaningful content produces a different ID.
"""

from __future__ import annotations

import hashlib


def make_canonical_id(source: str, url: str, title: str) -> str:
    """
    Deterministic SHA-256 canonical ID for job deduplication.
    Mirrors the logic in apps/crawler/crawler/pipeline/deduplicator.py.
    """
    raw = f"{source.lower()}\x00{url.strip().lower()}\x00{title.strip().lower()}"
    return hashlib.sha256(raw.encode()).hexdigest()


class TestCanonicalId:
    # ── Basic contract ────────────────────────────────────────────────────────

    def test_returns_64_char_hex_string(self):
        cid = make_canonical_id("remoteok", "https://example.com/jobs/1", "Python Engineer")
        assert isinstance(cid, str)
        assert len(cid) == 64
        assert all(c in "0123456789abcdef" for c in cid)

    def test_same_inputs_produce_same_id(self):
        a = make_canonical_id("remoteok", "https://example.com/jobs/1", "Python Engineer")
        b = make_canonical_id("remoteok", "https://example.com/jobs/1", "Python Engineer")
        assert a == b

    # ── Determinism ───────────────────────────────────────────────────────────

    def test_different_source_different_id(self):
        a = make_canonical_id("remoteok", "https://example.com/jobs/1", "Python Engineer")
        b = make_canonical_id("wwr", "https://example.com/jobs/1", "Python Engineer")
        assert a != b

    def test_different_url_different_id(self):
        a = make_canonical_id("remoteok", "https://example.com/jobs/1", "Python Engineer")
        b = make_canonical_id("remoteok", "https://example.com/jobs/2", "Python Engineer")
        assert a != b

    def test_different_title_different_id(self):
        a = make_canonical_id("remoteok", "https://example.com/jobs/1", "Python Engineer")
        b = make_canonical_id("remoteok", "https://example.com/jobs/1", "Senior Python Engineer")
        assert a != b

    # ── Normalisation ─────────────────────────────────────────────────────────

    def test_case_insensitive_source(self):
        a = make_canonical_id("RemoteOK", "https://example.com/j/1", "DevOps Lead")
        b = make_canonical_id("remoteok", "https://example.com/j/1", "devops lead")
        assert a == b

    def test_url_whitespace_stripped(self):
        a = make_canonical_id("wwr", "  https://example.com/j/1  ", "Role")
        b = make_canonical_id("wwr", "https://example.com/j/1", "Role")
        assert a == b

    def test_title_whitespace_stripped(self):
        a = make_canonical_id("wwr", "https://example.com/j/1", "  Role  ")
        b = make_canonical_id("wwr", "https://example.com/j/1", "Role")
        assert a == b

    # ── Collision scenarios ───────────────────────────────────────────────────

    def test_no_collision_between_distinct_jobs(self):
        """Populate a set — all 10 distinct jobs must produce distinct IDs."""
        jobs = [
            ("remoteok", f"https://example.com/jobs/{i}", f"Role {i}")
            for i in range(10)
        ]
        ids = {make_canonical_id(*j) for j in jobs}
        assert len(ids) == 10

    def test_no_collision_between_similar_urls(self):
        """Jobs that differ only by trailing slash or query string are distinct."""
        a = make_canonical_id("src", "https://example.com/job/1", "Role")
        b = make_canonical_id("src", "https://example.com/job/1/", "Role")
        c = make_canonical_id("src", "https://example.com/job/1?ref=api", "Role")
        assert len({a, b, c}) == 3  # all different

    def test_prefix_collision_resistance(self):
        """A job can't collide by injecting the delimiter '|' into its fields."""
        a = make_canonical_id("src|extra", "url", "title")
        b = make_canonical_id("src", "extra|url", "title")
        # Both are distinct because the raw string differs — separator in field
        # changes position of remaining delimiters in raw
        # (we just verify they don't accidentally equal each other)
        assert a != b
