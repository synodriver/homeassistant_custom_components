# -*- coding: utf-8 -*-
"""
Copyright (c) 2008-2024 synodriver <diguohuangjiajinweijun@gmail.com>
"""
import logging

from qingping_sdk import Client

import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import Event, HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.SENSOR,
]  # 我暂时只有个温湿度计，除非青萍打钱让我写其他的，不过其他的已经有人写了，唯独这两个“商用的”不能接米家啥的，只能曲线救国

from .consts import CONF_APP_KEY, CONF_APP_SECRET, DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the qingping component. 似乎是用户动态输入调用的"""
    _LOGGER.info(f"qingping in async_setup_entry")
    hass.data.setdefault(DOMAIN, {})
    conf = entry.data

    app_key: str = conf.get(CONF_APP_KEY)
    app_secret: str = conf.get(CONF_APP_SECRET)

    session = async_get_clientsession(hass)
    # create client
    client = Client(app_key, app_secret, client_session=session, close_on_exit=False)
    await client.__aenter__()  # 等待刷新access_token
    hass.data[DOMAIN]["qingping_client"] = client

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload qingping sensors."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        client: Client = hass.data[DOMAIN]["qingping_client"]
        await client.__aexit__(None, None, None)
        hass.data[DOMAIN].pop("qingping_client")
    _LOGGER.info(f"qingping in async_unload_entry {unload_ok}")
    return unload_ok
