"""Shared pieces for source adapters: the job shape, PII scrubbing, HTTP."""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Any, Self

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

USER_AGENT = "silabus/0.1 (job market research; contact via GitHub)"

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
# Indonesian mobile numbers, with or without the country code.
_PHONE = re.compile(r"(?<!\d)(?:\+62|62|0)[\s-]?8[1-9](?:[\s-]?\d){6,11}(?!\d)")
_SENSITIVE_KEY = re.compile(
    r"(?i)^(email|e-mail|phone|telepon|telp|mobile|recruiter.*|contact.*|.*_email|.*_phone)$"
)


@dataclass(frozen=True, slots=True)
class SourceJob:
    """One posting as a source reported it, before any normalization."""

    source: str
    external_id: str
    source_url: str
    title: str
    company: str | None
    location: str | None
    description_html: str | None
    posted_at_raw: str | None
    payload: dict[str, Any]


def redact_text(text: str) -> str:
    text = _EMAIL.sub("[email removed]", text)
    return _PHONE.sub("[phone removed]", text)


def scrub_payload(value: Any) -> Any:
    """Drop contact fields and redact emails and phone numbers.

    Runs before anything reaches raw_listings. Recruiter names and contact
    details are personal data under UU PDP 27/2022, and the pipeline has no use
    for them.
    """
    if isinstance(value, dict):
        return {
            key: scrub_payload(item)
            for key, item in value.items()
            if not _SENSITIVE_KEY.search(str(key))
        }
    if isinstance(value, list):
        return [scrub_payload(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


class PoliteClient:
    """HTTP client with a timeout, retries, an optional on-disk cache and an
    optional minimum delay between requests.

    JSON board endpoints do not need a delay. HTML sources do, and that is what
    `min_interval` is for.
    """

    def __init__(
        self,
        *,
        user_agent: str = USER_AGENT,
        timeout: float = 20.0,
        min_interval: float = 0.0,
        cache_dir: Path | None = None,
    ) -> None:
        self._client = httpx.Client(
            timeout=timeout,
            headers={"user-agent": user_agent},
            follow_redirects=True,
        )
        self._min_interval = min_interval
        self._last_request = 0.0
        self._cache_dir = cache_dir
        if cache_dir is not None:
            cache_dir.mkdir(parents=True, exist_ok=True)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def _wait(self) -> None:
        if self._min_interval <= 0:
            return
        elapsed = time.monotonic() - self._last_request
        remaining = self._min_interval - elapsed
        if remaining > 0:
            time.sleep(remaining)
        self._last_request = time.monotonic()

    def _cache_path(self, url: str) -> Path | None:
        if self._cache_dir is None:
            return None
        digest = hashlib.sha256(url.encode()).hexdigest()
        return self._cache_dir / f"{digest}.json"

    @retry(
        retry=retry_if_exception_type(httpx.HTTPError),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, max=30),
        reraise=True,
    )
    def get_json(self, url: str) -> Any:
        path = self._cache_path(url)
        if path is not None and path.exists():
            return json.loads(path.read_text())

        self._wait()
        response = self._client.get(url)
        response.raise_for_status()
        data: Any = response.json()

        if path is not None:
            path.write_text(json.dumps(data))
        return data
