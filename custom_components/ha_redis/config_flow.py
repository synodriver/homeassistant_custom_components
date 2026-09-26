"""Config flow for the Redis integration."""

from collections.abc import Mapping
from typing import Any, override

from redis import exceptions as redis_exceptions
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .client import create_redis_client
from .const import DEFAULT_PORT, DOMAIN

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Optional(CONF_USERNAME): cv.string,
        vol.Optional(CONF_PASSWORD): cv.string,
    }
)

REAUTH_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    }
)


class CannotConnect(HomeAssistantError):
    """Error to indicate the Redis server cannot be reached."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate the Redis credentials are invalid."""


async def validate_input(data: dict[str, Any]) -> None:
    """Validate that the entered details allow connecting to Redis."""
    client = create_redis_client(
        host=data[CONF_HOST],
        port=data[CONF_PORT],
        username=data.get(CONF_USERNAME),
        password=data.get(CONF_PASSWORD),
    )
    try:
        await client.ping()
    except redis_exceptions.AuthenticationError as err:
        raise InvalidAuth from err
    except (redis_exceptions.RedisError, OSError) as err:
        raise CannotConnect from err
    finally:
        await client.aclose()


class RedisConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Redis."""

    VERSION = 1

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = user_input[CONF_PORT]
            username = user_input.get(CONF_USERNAME, "").strip() or None
            password = user_input.get(CONF_PASSWORD)

            if not host:
                errors[CONF_HOST] = "invalid_host"
            else:
                normalized_host = host.lower()
                self._async_abort_entries_match(
                    {CONF_HOST: normalized_host, CONF_PORT: port}
                )
                await self.async_set_unique_id(f"{normalized_host}:{port}")
                self._abort_if_unique_id_configured()

                try:
                    await validate_input(
                        {
                            CONF_HOST: normalized_host,
                            CONF_PORT: port,
                            CONF_USERNAME: username,
                            CONF_PASSWORD: password,
                        }
                    )
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                except InvalidAuth:
                    errors["base"] = "invalid_auth"
                else:
                    data = {CONF_HOST: normalized_host, CONF_PORT: port}
                    if username:
                        data[CONF_USERNAME] = username
                    if password:
                        data[CONF_PASSWORD] = password
                    return self.async_create_entry(
                        title=f"{host}:{port}",
                        data=data,
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
        )

    @override
    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle a reauth flow when Redis authentication failed."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm the new Redis credentials."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()

        if user_input is not None:
            username = user_input.get(CONF_USERNAME, "").strip() or None
            password = user_input[CONF_PASSWORD]
            try:
                await validate_input(
                    {
                        CONF_HOST: entry.data[CONF_HOST],
                        CONF_PORT: entry.data[CONF_PORT],
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password or None,
                    }
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            else:
                data = {
                    CONF_HOST: entry.data[CONF_HOST],
                    CONF_PORT: entry.data[CONF_PORT],
                }
                if username:
                    data[CONF_USERNAME] = username
                if password:
                    data[CONF_PASSWORD] = password
                return self.async_update_reload_and_abort(entry, data=data)

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=self.add_suggested_values_to_schema(
                REAUTH_SCHEMA,
                {CONF_USERNAME: entry.data.get(CONF_USERNAME, "")},
            ),
            description_placeholders={"name": entry.title},
            errors=errors,
        )
