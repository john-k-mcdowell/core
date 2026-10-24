"""Tests for the Daikin climate entity HVAC action."""

import pytest
from pytest_homeassistant.common import MockConfigEntry

from homeassistant.components.climate import (
    ATTR_HVAC_ACTION,
    DOMAIN as CLIMATE_DOMAIN,
    HVACAction,
)
from homeassistant.components.daikin.const import DOMAIN, KEY_MAC
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .conftest import ZoneDevice, configure_zone_device

HOST = "127.0.0.1"


async def _async_setup_daikin(hass: HomeAssistant, device: ZoneDevice) -> str:
    """Set up the integration with a mocked device and return the climate entity."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=device.mac,
        data={CONF_HOST: HOST, KEY_MAC: device.mac},
    )
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    entity_id = er.async_get(hass).async_get_entity_id(
        CLIMATE_DOMAIN, DOMAIN, device.mac
    )
    assert entity_id is not None
    return entity_id


@pytest.mark.parametrize(
    ("mode", "equipment_active", "expected_action"),
    [
        ("cool", True, HVACAction.COOLING),
        ("cool", False, HVACAction.IDLE),
        ("hot", True, HVACAction.HEATING),
        ("hot", False, HVACAction.IDLE),
        ("off", False, HVACAction.OFF),
    ],
)
async def test_hvac_action_uses_equipment_active(
    hass: HomeAssistant,
    zone_device: ZoneDevice,
    mode: str,
    equipment_active: bool,
    expected_action: HVACAction,
) -> None:
    """A unit that reports whether it is active is idle when it is not."""
    configure_zone_device(zone_device, zones=[["Living", "1", 22]], mode=mode)
    zone_device.support_equipment_active = True
    zone_device.equipment_active = equipment_active

    entity_id = await _async_setup_daikin(hass, zone_device)

    state = hass.states.get(entity_id)
    assert state is not None
    assert state.attributes[ATTR_HVAC_ACTION] == expected_action


@pytest.mark.parametrize(
    ("mode", "expected_action"),
    [
        ("cool", HVACAction.COOLING),
        ("hot", HVACAction.HEATING),
    ],
)
async def test_hvac_action_without_activity_information(
    hass: HomeAssistant,
    zone_device: ZoneDevice,
    mode: str,
    expected_action: HVACAction,
) -> None:
    """A unit that cannot report activity keeps the action derived from the mode."""
    configure_zone_device(zone_device, zones=[["Living", "1", 22]], mode=mode)
    zone_device.support_equipment_active = False
    zone_device.equipment_active = None

    entity_id = await _async_setup_daikin(hass, zone_device)

    state = hass.states.get(entity_id)
    assert state is not None
    assert state.attributes[ATTR_HVAC_ACTION] == expected_action


@pytest.mark.parametrize(
    ("compressor_frequency", "expected_action"),
    [
        (0, HVACAction.IDLE),
        (40, HVACAction.COOLING),
    ],
)
async def test_hvac_action_uses_compressor_frequency(
    hass: HomeAssistant,
    zone_device: ZoneDevice,
    compressor_frequency: int,
    expected_action: HVACAction,
) -> None:
    """The compressor frequency still decides idle for units that report it."""
    configure_zone_device(zone_device, zones=[["Living", "1", 22]], mode="cool")
    zone_device.support_compressor_frequency = True
    zone_device.compressor_frequency = compressor_frequency

    entity_id = await _async_setup_daikin(hass, zone_device)

    state = hass.states.get(entity_id)
    assert state is not None
    assert state.attributes[ATTR_HVAC_ACTION] == expected_action
