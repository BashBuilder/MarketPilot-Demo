"""Signed HTTP access to Cloudinary.

The upload API signs the exact parameters it receives with the API secret, so
the signing helper lives next to the request builder. Transient failures
(timeouts, transport errors, 5xx) are retryable; a 4xx or malformed payload is
not, mirroring the image providers.
"""

import asyncio
import hashlib
import time

import httpx

from app.core.errors import ToolError


class CloudinaryClient:
    """Minimal Cloudinary upload/download client; no secret is logged."""

    def __init__(
        self,
        *,
        cloud_name: str,
        api_key: str,
        api_secret: str,
        timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not cloud_name.strip() or not api_key or not api_secret:
            raise ValueError("cloud_name, api_key and api_secret must not be empty")
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self._cloud_name = cloud_name.strip()
        self._api_key = api_key
        self._api_secret = api_secret
        self._timeout = timeout
        self._transport = transport

    async def upload(
        self,
        data: bytes,
        *,
        public_id: str,
        filename: str,
        content_type: str,
    ) -> dict[str, object]:
        """Upload bytes and return the Cloudinary response body."""
        fields = {
            "public_id": public_id,
            "overwrite": "true",
            "timestamp": str(int(time.time())),
        }
        payload = {
            **fields,
            "api_key": self._api_key,
            "signature": _sign(fields, self._api_secret),
        }
        response = await self._request(
            "POST",
            f"https://api.cloudinary.com/v1_1/{self._cloud_name}/image/upload",
            data=payload,
            files={"file": (filename, data, content_type)},
        )
        try:
            body = response.json()
        except ValueError as exc:
            raise ToolError("Cloudinary returned invalid JSON") from exc
        if not isinstance(body, dict):
            raise ToolError("Cloudinary returned an unexpected payload")
        return body

    async def download(self, url: str) -> bytes:
        """Fetch a stored asset over HTTPS; callers validate the bytes."""
        response = await self._request("GET", url)
        return response.content

    async def _request(
        self,
        method: str,
        url: str,
        *,
        data: dict[str, str] | None = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
    ) -> httpx.Response:
        try:
            response = await asyncio.wait_for(
                self._send(method, url, data=data, files=files),
                timeout=self._timeout,
            )
        except TimeoutError as exc:
            raise ToolError("Cloudinary request timed out", retryable=True) from exc
        return response

    async def _send(
        self,
        method: str,
        url: str,
        *,
        data: dict[str, str] | None,
        files: dict[str, tuple[str, bytes, str]] | None,
    ) -> httpx.Response:
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, transport=self._transport, follow_redirects=True
            ) as client:
                response = await client.request(method, url, data=data, files=files)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise ToolError("Cloudinary request timed out", retryable=True) from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise ToolError(
                f"Cloudinary returned HTTP {status}",
                retryable=status >= 500,
                details={"status": status},
            ) from exc
        except httpx.RequestError as exc:
            raise ToolError("Cloudinary request failed", retryable=True) from exc
        return response


def _sign(fields: dict[str, str], api_secret: str) -> str:
    """Sign the exact parameters sent, as Cloudinary's upload API expects."""
    query = "&".join(f"{key}={value}" for key, value in sorted(fields.items()))
    return hashlib.sha1(f"{query}{api_secret}".encode()).hexdigest()
