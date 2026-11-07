"""YouTube safe URL helper."""

from __future__ import annotations

import urllib.parse


def youtube_search_url(query: str) -> str:
    return "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query)

