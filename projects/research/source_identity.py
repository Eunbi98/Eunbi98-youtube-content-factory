from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


ACADEMIC_RESOLVER_HOSTS = {
    "doi.org",
    "dx.doi.org",
    "openalex.org",
    "api.openalex.org",
}


def source_identity(source: dict[str, Any]) -> str:
    """Return the publisher identity, or the work ID for academic resolvers."""

    url = str(source.get("source_url") or "").strip()
    host = urlparse(url).netloc.casefold()
    if not host:
        return ""
    if (
        source.get("source_tier") == "academic"
        and host in ACADEMIC_RESOLVER_HOSTS
    ):
        return f"academic-work:{url.casefold()}"
    return host


def source_identities(sources: list[dict[str, Any]]) -> set[str]:
    return {
        identity
        for source in sources
        if isinstance(source, dict)
        for identity in (source_identity(source),)
        if identity
    }
