"""Config flow for Fingerbot HTTP endpoints."""

from typing import Any, override
from urllib.parse import urlparse

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_URL
from homeassistant.helpers import config_validation as cv

from .const import CONF_ENDPOINT, DOMAIN


class FingerbotConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle manual setup of a Fingerbot endpoint."""

    VERSION = 1

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the HTTP endpoint."""
        errors: dict[str, str] = {}
        if user_input is not None:
            endpoint = user_input[CONF_URL].strip()
            try:
                endpoint = cv.url(endpoint)
                parsed = urlparse(endpoint)
                if parsed.scheme not in ("http", "https") or not parsed.hostname:
                    raise vol.Invalid("invalid endpoint")
            except (vol.Invalid, ValueError):
                errors[CONF_URL] = "invalid_url"
            else:
                self._async_abort_entries_match({CONF_ENDPOINT: endpoint})
                await self.async_set_unique_id(endpoint)
                self._abort_if_unique_id_configured()
                title = parsed.hostname or endpoint
                return self.async_create_entry(
                    title=f"Fingerbot ({title})",
                    data={CONF_ENDPOINT: endpoint},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_URL): cv.string}),
            errors=errors,
        )
