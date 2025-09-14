# -*- coding: utf-8 -*-
"""
Copyright (c) 2008-2024 synodriver <diguohuangjiajinweijun@gmail.com>
"""
import time
from datetime import timedelta
from typing import Dict, Literal

import qingping_sdk.exceptions
from qingping_sdk import Client

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
    EntityCategory,
    UnitOfPressure,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .consts import DOMAIN, QINGPING_URL

SCAN_INTERVAL = timedelta(minutes=1)

SENSOR_TYPES: Dict[str, SensorEntityDescription] = {
    "battery": SensorEntityDescription(
        key=f"qinping.battery",
        name="battery",
        translation_key=f"qinping.battery",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=True,
        icon="mdi:battery",
    ),
    "humidity": SensorEntityDescription(
        key=f"qinping.humidity",
        name="humidity",
        translation_key=f"qinping.humidity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=True,
        icon="mdi:water-percent",
    ),
    "pressure": SensorEntityDescription(
        key=f"qinping.pressure",
        name="pressure",
        translation_key=f"qinping.pressure",
        native_unit_of_measurement=UnitOfPressure.KPA,
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=True,
        icon="mdi:arrow-collapse-down",
    ),
    "temperature": SensorEntityDescription(
        key=f"qinping.temperature",
        name="temperature",
        translation_key=f"qinping.temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=True,
        icon="mdi:temperature-celsius",
    ),
    "tvoc": SensorEntityDescription(
        key=f"qinping.tvoc",
        name="tvoc",
        translation_key=f"qinping.tvoc",
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=True,
    ),
    "co2": SensorEntityDescription(
        key=f"qinping.co2",
        name="co2",
        translation_key=f"qinping.co2",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        device_class=SensorDeviceClass.CO2,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=True,
    ),
    "pm25": SensorEntityDescription(
        key=f"qinping.pm25",
        name="pm25",
        translation_key=f"qinping.pm25",
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        device_class=SensorDeviceClass.PM25,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=True,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    print("in async_setup_entry")
    client: Client = hass.data[DOMAIN]["qingping_client"]
    data = await client.get_devices()
    num_devices = data[
        "total"
    ]  # todo 看看是否需要分页 如果有土豪的设备多的需要分页的话一定会发现这个问题，得想办法要点赞助）

    sensors = []
    for d in data["devices"]:
        sn = await client.get_device_info(
            [d["info"]["mac"]], ["sn", "customization.sn"]
        )
        sn = sn["profiles"][0]
        if "sn" in sn:
            sn = sn["sn"]
        else:
            sn = None  # 青萍不给呜呜呜
        device_info = DeviceInfo(
            name=d["info"]["name"],
            configuration_url=QINGPING_URL,
            created_at=d["info"]["created_at"],
            identifiers={(DOMAIN, d["info"]["mac"])},
            sw_version=d["info"]["version"],
            model=d["info"]["product"]["name"],
            model_id=d["info"]["product"]["id"],
            serial_number=sn,
        )
        for field in d["data"]:
            des = SENSOR_TYPES.get(field, None)
            if des:
                sensors.append(
                    QingPingSensor(client, device_info, des, d["info"]["mac"], field)
                )
    async_add_entities(sensors)


class QingPingSensor(SensorEntity):
    _attr_should_poll = True

    def __init__(
        self,
        client: Client,
        device_info: DeviceInfo,
        description: SensorEntityDescription,
        mac: str,
        field: Literal[
            "battery", "temperature", "humidity", "pressure", "tvoc", "co2", "pm25"
        ],
    ):
        self.client = client
        self._attr_available = True
        self._attr_has_entity_name = True
        self.mac = mac
        self.field = field  # what sensor
        self._attr_unique_id = f"qingping_{mac}_{field}"
        self._attr_device_info = device_info
        # self._attr_entity_picture = (
        #     "https://www.qingping.co/static/media/air_selected.eb00d526.png"
        # )
        self.entity_description = description

    async def async_update(self):
        historydata = await self.client.get_history_data(
            self.mac, int(time.time()) - 600, int(time.time())
        )
        try:
            data: float = historydata["data"][-1][self.field]["value"]
            self._attr_native_value = data
            self._attr_available = True
        except IndexError:
            pass
        except qingping_sdk.exceptions.AuthException as err:
            raise ConfigEntryAuthFailed from err
        except:
            self._attr_available = False
