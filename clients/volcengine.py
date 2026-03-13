"""
Volcengine Ark API client for Seedream (image) / Seedance (video) generation.

Adapted from user-provided VolcengineArkClient.  Provides both async core and
synchronous helper wrappers (``sync_generate_image`` / ``sync_generate_video``)
for use inside agno workflow steps which are synchronous.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

ImageRef = tuple[str, str]


class VolcengineAPIError(RuntimeError):
    pass


class VolcengineArkClient:
    """Ark image/video generation client for Seedream/Seedance."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        timeout_sec: int = 120,
        poll_interval_sec: float = 4.0,
        poll_timeout_sec: int = 600,
    ) -> None:
        self._api_key = api_key.strip()
        self._base_url = base_url.rstrip("/")
        self._timeout_sec = timeout_sec
        self._poll_interval_sec = poll_interval_sec
        self._poll_timeout_sec = poll_timeout_sec
        self._client: httpx.AsyncClient | None = None

    @property
    def enabled(self) -> bool:
        return bool(self._api_key)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self._timeout_sec,
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _headers(self) -> dict[str, str]:
        if not self._api_key:
            raise VolcengineAPIError("missing VOLCENGINE_API_KEY")
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

    # -- image --

    async def generate_image(
        self,
        *,
        model: str,
        prompt: str,
        size: str = "2K",
        watermark: bool = False,
        references: list[ImageRef] | None = None,
    ) -> str:
        url = f"{self._base_url}/images/generations"
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "watermark": watermark,
        }
        if references:
            payload["image_urls"] = [
                {"role": role, "url": image_url}
                for role, image_url in references
                if image_url
            ]

        client = await self._get_client()
        response = await client.post(url, headers=self._headers(), json=payload)

        if response.status_code >= 400:
            raise VolcengineAPIError(
                f"image generation failed: {response.status_code} {response.text}"
            )

        data = response.json()
        image_url = self._extract_image_url(data)
        if not image_url:
            raise VolcengineAPIError(f"image generation missing url: {data}")
        return image_url

    # -- video --

    async def generate_video(
        self,
        *,
        model: str,
        prompt: str,
        ratio: str = "9:16",
        duration_sec: int = 5,
        watermark: bool = False,
        references: list[ImageRef] | None = None,
    ) -> tuple[str, str]:
        task_id = await self.submit_video_task(
            model=model,
            prompt=prompt,
            ratio=ratio,
            duration_sec=duration_sec,
            watermark=watermark,
            references=references,
        )
        video_url = await self.poll_video_task(task_id)
        return task_id, video_url

    async def submit_video_task(
        self,
        *,
        model: str,
        prompt: str,
        ratio: str,
        duration_sec: int,
        watermark: bool = False,
        references: list[ImageRef] | None = None,
    ) -> str:
        url = f"{self._base_url}/contents/generations/tasks"
        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        for _role, image_url in references or []:
            if not image_url:
                continue
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": image_url},
                }
            )
            break

        payload = {
            "model": model,
            "content": content,
            "ratio": ratio,
            "duration": duration_sec,
            "watermark": watermark,
        }

        client = await self._get_client()
        response = await client.post(url, headers=self._headers(), json=payload)

        if response.status_code >= 400:
            logger.error(
                "video submit failed",
                extra={"url": url, "status_code": response.status_code, "text": response.text},
            )
            raise VolcengineAPIError(
                f"video submit failed: {response.status_code} {response.text}"
            )

        data = response.json()
        task_id = str(data.get("id") or "").strip()
        if not task_id:
            logger.error("video submit missing task id", extra={"url": url, "data": data})
            raise VolcengineAPIError(f"video submit missing task id: {data}")
        return task_id

    async def poll_video_task(self, task_id: str) -> str:
        url = f"{self._base_url}/contents/generations/tasks/{task_id}"
        elapsed = 0.0

        client = await self._get_client()
        while elapsed <= self._poll_timeout_sec:
            response = await client.get(url, headers=self._headers())
            if response.status_code >= 400:
                logger.error(
                    "video poll failed",
                    extra={"url": url, "status_code": response.status_code, "text": response.text},
                )
                raise VolcengineAPIError(
                    f"video poll failed: {response.status_code} {response.text}"
                )

            data = response.json()
            status = str(data.get("status") or "").lower()

            if status in {"succeeded", "success", "completed"}:
                video_url = self._extract_video_url(data)
                if not video_url:
                    logger.error(
                        "video success but url missing", extra={"url": url, "data": data}
                    )
                    raise VolcengineAPIError(f"video success but url missing: {data}")
                return video_url

            if status in {"failed", "error", "cancelled", "canceled"}:
                logger.error("video task failed", extra={"url": url, "data": data})
                raise VolcengineAPIError(f"video task failed: {data}")

            await asyncio.sleep(self._poll_interval_sec)
            elapsed += self._poll_interval_sec

        logger.error("video task poll timeout", extra={"url": url, "task_id": task_id})
        raise VolcengineAPIError(f"video task poll timeout: task_id={task_id}")

    # -- response extractors --

    @staticmethod
    def _extract_image_url(data: dict[str, Any]) -> str:
        rows = data.get("data")
        if isinstance(rows, list) and rows:
            first = rows[0]
            if isinstance(first, dict):
                for key in ("url", "image_url"):
                    val = first.get(key)
                    if isinstance(val, str) and val:
                        return val
                resource = first.get("resource")
                if isinstance(resource, dict):
                    for key in ("url", "image_url"):
                        val = resource.get(key)
                        if isinstance(val, str) and val:
                            return val

        for key in ("url", "image_url"):
            val = data.get(key)
            if isinstance(val, str) and val:
                return val

        output = data.get("output")
        if isinstance(output, dict):
            for key in ("url", "image_url"):
                val = output.get(key)
                if isinstance(val, str) and val:
                    return val

        return ""

    @staticmethod
    def _extract_video_url(data: dict[str, Any]) -> str:
        for root_key in ("content", "output", "result"):
            root = data.get(root_key)
            if isinstance(root, dict):
                for key in ("video_url", "url"):
                    val = root.get(key)
                    if isinstance(val, str) and val:
                        return val
                resources = root.get("resources")
                if isinstance(resources, list):
                    for item in resources:
                        if isinstance(item, dict):
                            for key in ("video_url", "url"):
                                val = item.get(key)
                                if isinstance(val, str) and val:
                                    return val

        for key in ("video_url", "url"):
            val = data.get(key)
            if isinstance(val, str) and val:
                return val

        return ""


# ---------------------------------------------------------------------------
# Singleton & synchronous wrappers for use in agno workflow steps
# ---------------------------------------------------------------------------

_ark_client: VolcengineArkClient | None = None


def get_ark_client() -> VolcengineArkClient:
    global _ark_client  # noqa: PLW0603
    if _ark_client is None:
        _ark_client = VolcengineArkClient(
            api_key=os.getenv("VOLCENGINE_API_KEY", ""),
            base_url=os.getenv(
                "VOLCENGINE_BASE_URL",
                "https://ark.cn-beijing.volces.com/api/v3",
            ),
        )
    return _ark_client


def sync_generate_image(
    prompt: str,
    *,
    references: list[ImageRef] | None = None,
    size: str = "2K",
) -> str | None:
    """Synchronous image generation.  Returns URL or *None* when disabled."""
    client = get_ark_client()
    if not client.enabled:
        logger.warning("volcengine image generation skipped: no API key configured")
        return None
    model = os.getenv("VOLCENGINE_IMAGE_MODEL", "seedream-3.0")
    return asyncio.run(
        client.generate_image(
            model=model, prompt=prompt, size=size, references=references,
        )
    )


def sync_generate_video(
    prompt: str,
    *,
    references: list[ImageRef] | None = None,
    ratio: str = "9:16",
    duration_sec: int = 5,
) -> tuple[str, str] | None:
    """Synchronous video generation.  Returns (task_id, video_url) or *None*."""
    client = get_ark_client()
    if not client.enabled:
        logger.warning("volcengine video generation skipped: no API key configured")
        return None
    model = os.getenv("VOLCENGINE_VIDEO_MODEL", "seedance-1.0")
    return asyncio.run(
        client.generate_video(
            model=model, prompt=prompt, ratio=ratio,
            duration_sec=duration_sec, references=references,
        )
    )
