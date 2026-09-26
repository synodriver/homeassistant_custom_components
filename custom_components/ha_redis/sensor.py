"""Support for Redis server metrics exposed as sensors."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import override

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfInformation, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import RedisConfigEntry, RedisUpdateCoordinator

type RedisSensorValue = int | float | str | datetime


@dataclass(frozen=True, kw_only=True)
class RedisSensorEntityDescription(SensorEntityDescription):
    """Describe a Redis sensor entity."""

    value_converter: Callable[[str], RedisSensorValue]


def _as_datetime(value: str) -> datetime:
    """Convert a Redis unix timestamp to an aware datetime."""
    return dt_util.utc_from_timestamp(int(value))


def _description(
    key: str,
    converter: Callable[[str], RedisSensorValue],
    *,
    device_class: SensorDeviceClass | None = None,
    native_unit_of_measurement: str | None = None,
    state_class: SensorStateClass | None = None,
    suggested_display_precision: int | None = None,
) -> RedisSensorEntityDescription:
    """Create a sensor description from a Redis INFO key."""
    return RedisSensorEntityDescription(
        key=key,
        translation_key=key,
        device_class=device_class,
        native_unit_of_measurement=native_unit_of_measurement,
        state_class=state_class,
        suggested_display_precision=suggested_display_precision,
        value_converter=converter,
    )


SENSOR_DESCRIPTIONS: tuple[RedisSensorEntityDescription, ...] = (
    _description("redis_version", str),
    _description("redis_mode", str),
    _description("process_id", int, state_class=SensorStateClass.MEASUREMENT),
    _description("tcp_port", int, state_class=SensorStateClass.MEASUREMENT),
    _description("hz", int, state_class=SensorStateClass.MEASUREMENT),
    _description("connected_clients", int, state_class=SensorStateClass.MEASUREMENT),
    _description("maxclients", int, state_class=SensorStateClass.MEASUREMENT),
    _description("blocked_clients", int, state_class=SensorStateClass.MEASUREMENT),
    _description("pubsub_clients", int, state_class=SensorStateClass.MEASUREMENT),
    _description("pubsub_channels", int, state_class=SensorStateClass.MEASUREMENT),
    _description("pubsub_patterns", int, state_class=SensorStateClass.MEASUREMENT),
    _description(
        "used_memory",
        int,
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    _description(
        "used_memory_rss",
        int,
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    _description(
        "used_memory_peak",
        int,
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    _description(
        "used_memory_overhead",
        int,
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    _description(
        "used_memory_startup",
        int,
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    _description(
        "used_memory_dataset",
        int,
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    _description(
        "maxmemory",
        int,
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    _description("maxmemory_policy", str),
    _description(
        "total_system_memory",
        int,
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    _description(
        "mem_fragmentation_ratio",
        float,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
    ),
    _description(
        "allocator_frag_ratio",
        float,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
    ),
    _description(
        "allocator_rss_ratio",
        float,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
    ),
    _description(
        "lazyfree_pending_objects", int, state_class=SensorStateClass.MEASUREMENT
    ),
    _description("loading", int, state_class=SensorStateClass.MEASUREMENT),
    _description(
        "rdb_bgsave_in_progress", int, state_class=SensorStateClass.MEASUREMENT
    ),
    _description("rdb_last_bgsave_status", str),
    _description(
        "rdb_changes_since_last_save", int, state_class=SensorStateClass.MEASUREMENT
    ),
    _description(
        "rdb_last_save_time", _as_datetime, device_class=SensorDeviceClass.TIMESTAMP
    ),
    _description("aof_enabled", int, state_class=SensorStateClass.MEASUREMENT),
    _description(
        "aof_rewrite_in_progress", int, state_class=SensorStateClass.MEASUREMENT
    ),
    _description("aof_last_write_status", str),
    _description(
        "total_connections_received",
        int,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    _description(
        "rejected_connections", int, state_class=SensorStateClass.TOTAL_INCREASING
    ),
    _description(
        "total_commands_processed", int, state_class=SensorStateClass.TOTAL_INCREASING
    ),
    _description(
        "instantaneous_ops_per_sec", int, state_class=SensorStateClass.MEASUREMENT
    ),
    _description(
        "total_net_input_bytes",
        int,
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
    ),
    _description(
        "total_net_output_bytes",
        int,
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
    ),
    _description(
        "instantaneous_input_kbps",
        float,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
    ),
    _description(
        "instantaneous_output_kbps",
        float,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
    ),
    _description("keyspace_hits", int, state_class=SensorStateClass.TOTAL_INCREASING),
    _description("keyspace_misses", int, state_class=SensorStateClass.TOTAL_INCREASING),
    _description("expired_keys", int, state_class=SensorStateClass.TOTAL_INCREASING),
    _description("evicted_keys", int, state_class=SensorStateClass.TOTAL_INCREASING),
    _description("sync_full", int, state_class=SensorStateClass.TOTAL_INCREASING),
    _description("sync_partial_ok", int, state_class=SensorStateClass.TOTAL_INCREASING),
    _description(
        "sync_partial_err", int, state_class=SensorStateClass.TOTAL_INCREASING
    ),
    _description(
        "latest_fork_usec",
        int,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MICROSECONDS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    _description(
        "total_reads_processed", int, state_class=SensorStateClass.TOTAL_INCREASING
    ),
    _description(
        "total_writes_processed", int, state_class=SensorStateClass.TOTAL_INCREASING
    ),
    _description(
        "total_error_replies", int, state_class=SensorStateClass.TOTAL_INCREASING
    ),
    _description("role", str),
    _description("connected_slaves", int, state_class=SensorStateClass.MEASUREMENT),
    _description("master_link_status", str),
    _description(
        "repl_backlog_size",
        int,
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    _description(
        "used_cpu_sys",
        float,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=3,
    ),
    _description(
        "used_cpu_user",
        float,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=3,
    ),
    _description(
        "used_cpu_sys_children",
        float,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=3,
    ),
    _description(
        "used_cpu_user_children",
        float,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=3,
    ),
    _description("keyspace_keys", int, state_class=SensorStateClass.MEASUREMENT),
    _description("keyspace_expires", int, state_class=SensorStateClass.MEASUREMENT),
    _description("database_count", int, state_class=SensorStateClass.MEASUREMENT),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RedisConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Redis sensors from a config entry."""
    coordinator = entry.runtime_data.coordinator
    assert isinstance(coordinator, RedisUpdateCoordinator)
    async_add_entities(
        RedisSensor(coordinator, entry, description)
        for description in SENSOR_DESCRIPTIONS
    )


class RedisSensor(CoordinatorEntity[RedisUpdateCoordinator], SensorEntity):
    """Representation of a Redis INFO metric."""

    entity_description: RedisSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RedisUpdateCoordinator,
        entry: RedisConfigEntry,
        description: RedisSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        assert entry.unique_id is not None
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={
                (DOMAIN, entry.entry_id),
                (DOMAIN, entry.unique_id),
            },
        )

    @property
    @override
    def native_value(self) -> RedisSensorValue | None:
        """Return the value reported by Redis INFO."""
        if self.coordinator.data is None:
            return None
        raw_value = self.coordinator.data.get(self.entity_description.key)
        if raw_value is None:
            return None
        try:
            return self.entity_description.value_converter(raw_value)
        except ValueError:
            return None
