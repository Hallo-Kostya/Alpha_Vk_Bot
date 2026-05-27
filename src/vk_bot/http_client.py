import aiohttp
import asyncio
from src.common.logger import logger
from typing import Literal
from src.common.constants import HTTP_TIMEOUT

HTTP_METHOD = Literal["POST", "GET", "DELETE", "PATCH", "PUT"]


class HttpClient:
    def __init__(self, session: aiohttp.ClientSession):
        self._session = session

    async def _request(
        self,
        url: str,
        method: HTTP_METHOD,
        timeout: aiohttp.ClientTimeout = aiohttp.ClientTimeout(HTTP_TIMEOUT),
        **kwargs,
    ) -> list | dict | None:
        try:
            response = await self._session.request(
                method=method,
                url=url,
                timeout=timeout,
                **kwargs,
            )
            response.raise_for_status()
            return await response.json()
        except aiohttp.ClientResponseError as e:
            logger.error("Got Error while requesting url: %s, code: %s", url, e.status)
        except asyncio.TimeoutError as e:
            logger.exception(e)
        return None

    async def get(
        self,
        url: str,
        params: dict | None = None,
        headers: dict | None = None,
        **kwargs,
    ) -> list | dict | None:
        response_json = await self._request(
            url=url,
            method="GET",
            params=params,
            headers=headers,
            **kwargs,
        )
        return response_json

    async def post(
        self,
        url: str,
        headers: dict | None = None,
        data: dict | None = None,
        json: dict | None = None,
        **kwargs,
    ) -> list | dict | None:
        response_json = await self._request(
            url=url,
            method="POST",
            headers=headers,
            data=data,
            json=json,
            **kwargs,
        )
        return response_json

    async def patch(
        self,
        url: str,
        headers: dict | None = None,
        body: dict | None = None,
        **kwargs,
    ) -> list | dict | None:
        response_json = await self._request(
            url=url,
            method="PATCH",
            json=body,
            headers=headers,
            **kwargs,
        )
        return response_json

    async def delete(
        self,
        url: str,
        headers: dict | None = None,
        **kwargs,
    ) -> list | dict | None:
        response_json = await self._request(
            url=url,
            method="DELETE",
            headers=headers,
            **kwargs,
        )
        return response_json
