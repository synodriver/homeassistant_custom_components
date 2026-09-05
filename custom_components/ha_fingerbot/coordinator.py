"""Coordinator and HTTP client for Fingerbot devices."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
import logging

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_ENDPOINT,
    DEFAULT_CONTINUE_NUM,
    DEFAULT_CONTINUE_TIME,
    DEFAULT_LAST_TIME,
    DEFAULT_PUSH_DEPTH,
    DOMAIN,
    PARAM_CONTINUE_NUM,
    PARAM_CONTINUE_TIME,
    PARAM_LAST_TIME,
    PARAM_PUSH_DEPTH,
)

_LOGGER = logging.getLogger(__name__)
_REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15)


@dataclass(frozen=True, slots=True)
class FingerbotParameters:
    """Parameters sent to the Fingerbot API."""

    push_depth: int = DEFAULT_PUSH_DEPTH
    last_time: int = DEFAULT_LAST_TIME
    continue_num: int = DEFAULT_CONTINUE_NUM
    continue_time: int = DEFAULT_CONTINUE_TIME

    def as_query(self) -> dict[str, int]:
        """Return the API's camel-case query parameters."""
        return {
            PARAM_PUSH_DEPTH: self.push_depth,
            PARAM_LAST_TIME: self.last_time,
            PARAM_CONTINUE_NUM: self.continue_num,
            PARAM_CONTINUE_TIME: self.continue_time,
        }


type FingerbotConfigEntry = ConfigEntry["FingerbotCoordinator"]


class FingerbotCoordinator(DataUpdateCoordinator[FingerbotParameters]):
    """Coordinate parameter state and HTTP commands for one Fingerbot."""

    config_entry: FingerbotConfigEntry

    def __init__(self, hass: HomeAssistant, entry: FingerbotConfigEntry) -> None:
        """Initialize the coordinator with Home Assistant's shared session."""
        super().__init__(
            hass,
            _LOGGER,
            name=entry.title,
            config_entry=entry,
            update_interval=None,
            always_update=False,
        )
        self.endpoint = str(entry.data[CONF_ENDPOINT])
        self.session = async_get_clientsession(hass)
        self._request_lock = asyncio.Lock()
        self.data = FingerbotParameters()
        self.last_command_success: bool | None = None

    @property
    def device_info(self) -> DeviceInfo:
        """Return common device registry metadata."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.endpoint)},
            name=self.config_entry.title,
            manufacturer="兴盛控制",
            model="HTTP",
        )

    async def async_set_parameter(self, key: str, value: float) -> None:
        """Update one parameter without contacting the device."""
        integer_value = int(value)
        updates: dict[str, FingerbotParameters] = {
            PARAM_PUSH_DEPTH: replace(self.data, push_depth=integer_value),
            PARAM_LAST_TIME: replace(self.data, last_time=integer_value),
            PARAM_CONTINUE_NUM: replace(self.data, continue_num=integer_value),
            PARAM_CONTINUE_TIME: replace(self.data, continue_time=integer_value),
        }
        # 修改本地参数不代表设备已重新连通，保留最近一次 HTTP 请求的可用性。
        self.data = updates[key]
        self.async_update_listeners()

    async def async_press(self, parameters: FingerbotParameters | None = None) -> None:
        """Execute the Fingerbot HTTP action."""
        payload = parameters or self.data
        try:
            async with self._request_lock:
                # 保留用户输入的完整路径，反向代理场景下不能自行拼接 URL。
                async with self.session.get(
                    self.endpoint,
                    params=payload.as_query(),
                    timeout=_REQUEST_TIMEOUT,
                ) as response:
                    response.raise_for_status()
        except (aiohttp.ClientError, OSError, TimeoutError) as err:
            self.last_command_success = False
            self.async_update_listeners()
            raise HomeAssistantError(
                f"Failed to control Fingerbot at {self.endpoint}: {err}"
            ) from err

        self.last_command_success = True
        self.async_update_listeners()

    async def _async_update_data(self) -> FingerbotParameters:
        """Return cached parameters; the device exposes no read endpoint."""
        return self.data
