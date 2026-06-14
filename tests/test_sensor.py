# ruff: noqa: S101

"""Tests for the SAVS sensor platform."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast
from unittest.mock import Mock, patch

import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorEntityDescription

from custom_components.savs.const import DOMAIN
from custom_components.savs.sensor import SavsSensor, async_setup_entry

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry

EXPECTED_PROPERTY_SENSOR_COUNT = 6
EXPECTED_FIRE_SENSOR_COUNT = 3
EXPECTED_CONNECTIVITY_SENSOR_COUNT = 4
EXPECTED_BATTERY = 100.0
EXPECTED_ZIGBEE_OPTIONS = ["Good", "Average", "Poor", "Abnormal", "Not loaded"]
GATEWAY_ID = "CB07EB7RDE3669E"
SUB_DEVICE_IDS = {
    "CB07EB7RDE3669E_BM0A6E6PDE91F77",
    "CB07EB7RDE3669E_BM0A6E6PDE310C0",
    "CB07EB7RDE3669E_BM0A6E6PDEF1C13",
}


class FakeCoordinator:
    """Minimal coordinator for sensor tests."""

    def __init__(self, entry: MockConfigEntry, data: dict[str, Any]) -> None:
        """Initialize the fake coordinator."""
        self.config_entry = entry
        self.data = data


def device_id_for(entity: SavsSensor) -> str:
    """Return the SAVS device id from an entity's device info."""
    identifiers = cast("set[tuple[str, str]]", entity.device_info["identifiers"])
    domain, device_id = next(iter(identifiers))
    assert domain == DOMAIN
    return device_id


def coordinator_devices(page_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Transform API page data into coordinator device dicts."""
    devices: list[dict[str, Any]] = []
    for main_device in page_data:
        devices.append(
            {
                "device_id": main_device["deviceId"],
                "name": main_device["name"],
                "product_id": main_device["productId"],
                "product_sub_type": main_device["productSubType"],
                "model": main_device["productSubType"],
                "pic_url": main_device["picUrl"],
                "is_gateway": True,
                "properties": main_device.get("properties", []),
                "alarm_status": main_device["alarmStatus"],
                "fault_status": main_device["faultStatus"],
                "on_off_line_status": main_device["onOffLineStatus"],
                "device_online_status": main_device["deviceOnlineStatus"],
                "relation": main_device["relation"],
            }
        )
        devices.extend(
            {
                "device_id": (f"{sub_device['deviceId']}_{sub_device['subDeviceId']}"),
                "name": sub_device["subDeviceName"],
                "product_id": sub_device["subDeviceProductId"],
                "product_sub_type": sub_device["subDeviceProductSubType"],
                "model": sub_device["subDeviceModel"],
                "pic_url": sub_device["picUrl"],
                "is_gateway": False,
                "parent_device_id": main_device["deviceId"],
                "properties": sub_device["properties"],
                "alarm_status": sub_device["alarmStatus"],
                "fault_status": sub_device["faultStatus"],
                "on_off_line_status": sub_device["onOffLineStatus"],
                "device_online_status": sub_device.get("deviceOnlineStatus"),
            }
            for sub_device in main_device["subDeviceList"]
        )
    return devices


added_entities: list[SavsSensor] = []


@pytest.fixture(autouse=True)
def reset_added_entities() -> None:
    """Reset the collected entities before each test."""
    added_entities.clear()


def add_entities(entities: Sequence[SavsSensor]) -> None:
    """Collect entities added by async_setup_entry."""
    added_entities.extend(entities)


@pytest.mark.asyncio
async def test_async_setup_entry_creates_expected_sensors(
    hass: HomeAssistant,
    savs_config_entry: MockConfigEntry,
    load_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """Test that sensor setup creates property, fire, and connectivity sensors."""
    del hass
    page_data = load_fixture("devices.json")["data"]["pageData"]
    coordinator = FakeCoordinator(
        savs_config_entry,
        {"devices": coordinator_devices(page_data)},
    )
    savs_config_entry.runtime_data = Mock(coordinator=coordinator)

    await async_setup_entry(
        hass=Mock(),
        entry=cast("Any", savs_config_entry),
        async_add_entities=add_entities,
    )

    property_sensors = [
        entity
        for entity in added_entities
        if entity.entity_description.key in {"battery", "zigbee_signal"}
    ]
    fire_sensors = [
        entity
        for entity in added_entities
        if entity.entity_description.key == "fire_detected"
    ]
    connectivity_sensors = [
        entity
        for entity in added_entities
        if entity.entity_description.key == "connectivity"
    ]

    assert len(property_sensors) == EXPECTED_PROPERTY_SENSOR_COUNT
    assert len(fire_sensors) == EXPECTED_FIRE_SENSOR_COUNT
    assert len(connectivity_sensors) == EXPECTED_CONNECTIVITY_SENSOR_COUNT
    assert {
        device_id_for(entity) for entity in property_sensors + fire_sensors
    } == SUB_DEVICE_IDS
    assert {device_id_for(entity) for entity in connectivity_sensors} == {
        GATEWAY_ID,
        *SUB_DEVICE_IDS,
    }


def test_sensor_value_mapping_for_representative_device(
    savs_config_entry: MockConfigEntry,
    load_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """Test sensor value extraction against the representative device payload."""
    smoke_detector = load_fixture("devices.json")["data"]["pageData"][0][
        "subDeviceList"
    ][0]
    smoke_detector["device_id"] = (
        f"{smoke_detector['deviceId']}_{smoke_detector['subDeviceId']}"
    )
    smoke_detector["name"] = smoke_detector["subDeviceName"]
    smoke_detector["model"] = smoke_detector["subDeviceModel"]
    smoke_detector["room_name"] = smoke_detector["roomName"]
    smoke_detector["parent_device_id"] = smoke_detector["deviceId"]
    smoke_detector["product_id"] = smoke_detector["subDeviceProductId"]
    smoke_detector["product_sub_type"] = smoke_detector["subDeviceProductSubType"]
    smoke_detector["on_off_line_status"] = smoke_detector["onOffLineStatus"]
    smoke_detector["alarm_status"] = smoke_detector["alarmStatus"]
    smoke_detector["fault_status"] = smoke_detector["faultStatus"]

    battery_sensor = SavsSensor(
        coordinator=FakeCoordinator(savs_config_entry, {"devices": [smoke_detector]}),
        device_data=smoke_detector,
        description=SensorEntityDescription(key="battery", name="Battery"),
    )
    zigbee_sensor = SavsSensor(
        coordinator=FakeCoordinator(savs_config_entry, {"devices": [smoke_detector]}),
        device_data=smoke_detector,
        description=SensorEntityDescription(
            key="zigbee_signal",
            name="Zigbee Signal",
            device_class=SensorDeviceClass.ENUM,
        ),
    )

    assert SavsSensor._get_property_value(smoke_detector, "battery") == EXPECTED_BATTERY  # noqa: SLF001
    assert SavsSensor._get_property_value(smoke_detector, "zigbee_signal") == "Good"  # noqa: SLF001
    assert SavsSensor._get_property_value(smoke_detector, "connectivity") == "Online"  # noqa: SLF001
    assert SavsSensor._get_property_value(smoke_detector, "fire_detected") is False  # noqa: SLF001
    assert (
        battery_sensor._attr_unique_id  # noqa: SLF001
        == "01HXSAVSTEST00000000000000_CB07EB7RDE3669E_BM0A6E6PDE91F77_battery"
    )
    assert zigbee_sensor._attr_options == EXPECTED_ZIGBEE_OPTIONS  # noqa: SLF001


def test_sensor_value_mapping_handles_offline_and_fire_detected(
    load_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """Test connectivity and fire-detected value mapping edge cases."""
    smoke_detector = load_fixture("devices.json")["data"]["pageData"][0][
        "subDeviceList"
    ][0]
    offline_device = {**smoke_detector, "on_off_line_status": 0}
    fire_device = {**smoke_detector, "alarm_status": 0}
    missing_battery_device = {
        **smoke_detector,
        "properties": [
            prop
            for prop in smoke_detector["properties"]
            if prop["propertyIdentifier"] != "batteryCapacity"
        ],
    }

    assert SavsSensor._get_property_value(offline_device, "connectivity") == "Offline"  # noqa: SLF001
    assert SavsSensor._get_property_value(fire_device, "fire_detected") is True  # noqa: SLF001
    assert SavsSensor._get_property_value(missing_battery_device, "battery") is None  # noqa: SLF001


def test_handle_coordinator_update_updates_value_and_options(
    savs_config_entry: MockConfigEntry,
    load_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """Test coordinator updates refresh native value and enum options."""
    smoke_detector = load_fixture("devices.json")["data"]["pageData"][0][
        "subDeviceList"
    ][0]
    smoke_detector["device_id"] = (
        f"{smoke_detector['deviceId']}_{smoke_detector['subDeviceId']}"
    )
    smoke_detector["name"] = smoke_detector["subDeviceName"]
    smoke_detector["model"] = smoke_detector["subDeviceModel"]
    smoke_detector["room_name"] = smoke_detector["roomName"]
    smoke_detector["parent_device_id"] = smoke_detector["deviceId"]
    smoke_detector["product_id"] = smoke_detector["subDeviceProductId"]
    smoke_detector["product_sub_type"] = smoke_detector["subDeviceProductSubType"]
    coordinator = FakeCoordinator(savs_config_entry, {"devices": [smoke_detector]})
    sensor = SavsSensor(
        coordinator=coordinator,
        device_data=smoke_detector,
        description=SensorEntityDescription(
            key="zigbee_signal",
            name="Zigbee Signal",
            device_class=SensorDeviceClass.ENUM,
        ),
    )
    smoke_detector["properties"][1]["propertyValue"] = 2

    with patch.object(sensor, "async_write_ha_state") as async_write_ha_state:
        sensor._handle_coordinator_update()  # noqa: SLF001

    assert sensor.native_value == "Average"
    assert sensor._attr_options == EXPECTED_ZIGBEE_OPTIONS  # noqa: SLF001
    async_write_ha_state.assert_called_once()


def test_invalid_enum_protocol_does_not_set_options(
    savs_config_entry: MockConfigEntry,
    load_fixture: Callable[[str], dict[str, Any]],
) -> None:
    """Test invalid enum protocol JSON is ignored."""
    smoke_detector = load_fixture("devices.json")["data"]["pageData"][0][
        "subDeviceList"
    ][0]
    smoke_detector["device_id"] = (
        f"{smoke_detector['deviceId']}_{smoke_detector['subDeviceId']}"
    )
    smoke_detector["name"] = smoke_detector["subDeviceName"]
    smoke_detector["model"] = smoke_detector["subDeviceModel"]
    smoke_detector["room_name"] = smoke_detector["roomName"]
    smoke_detector["parent_device_id"] = smoke_detector["deviceId"]
    smoke_detector["product_id"] = smoke_detector["subDeviceProductId"]
    smoke_detector["product_sub_type"] = smoke_detector["subDeviceProductSubType"]
    smoke_detector["properties"][1]["propertyProtocol"] = "not-json"

    sensor = SavsSensor(
        coordinator=FakeCoordinator(savs_config_entry, {"devices": [smoke_detector]}),
        device_data=smoke_detector,
        description=SensorEntityDescription(
            key="zigbee_signal",
            name="Zigbee Signal",
            device_class=SensorDeviceClass.ENUM,
        ),
    )

    assert SavsSensor._parse_enum_protocol("not-json") is None  # noqa: SLF001
    assert not hasattr(sensor, "_attr_options")
