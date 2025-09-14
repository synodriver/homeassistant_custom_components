# -*- coding: utf-8 -*-
"""
Copyright (c) 2008-2024 synodriver <diguohuangjiajinweijun@gmail.com>
"""
from typing import Any

import voluptuous as vol
from qingping_sdk import Client
from qingping_sdk.exceptions import QingpingException

import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .consts import CONF_APP_KEY, CONF_APP_SECRET, DOMAIN

# from homeassistant.helpers.aiohttp_client import async_get_clientsession


class QingPingConfigFlow(ConfigFlow, domain=DOMAIN):
    """QingPing config flow."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        errors: dict[str, str] = {}
        if user_input:
            self._async_abort_entries_match({CONF_APP_KEY: user_input[CONF_APP_KEY]})
            try:
                client = Client(user_input[CONF_APP_KEY], user_input[CONF_APP_SECRET])
                await client._get_access_token()
            except QingpingException as e:
                errors["base"] = str(e)
            else:
                await client.aclose()
                return self.async_create_entry(
                    title="QingPingIntegration",
                    data=user_input,
                )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_APP_KEY): cv.string,
                    vol.Required(CONF_APP_SECRET): cv.string,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(self, user_input: dict[str, Any] | None = None):
        return self.async_step_user(user_input)
