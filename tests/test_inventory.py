from msfs_peripherals_bridge.devices.inventory import (
    InventoryItem,
    RawDevice,
    classify,
)
from msfs_peripherals_bridge.models import DeviceCatalog, DeviceDef


def _catalog(*defs: DeviceDef) -> DeviceCatalog:
    return DeviceCatalog(devices=list(defs))


YOKE = DeviceDef(
    id="yoke", name="Fulcrum One Yoke", vendor="0000", product="0000", name_match="Fulcrum"
)
PANEL = DeviceDef(
    id="switch_panel",
    name="Saitek Switch Panel",
    vendor="06a3",
    product="0d67",
    transport="hidraw",
)


def _item(items: list[InventoryItem], usb: str) -> InventoryItem:
    return next(it for it in items if it.usb == usb)


def test_registered_evdev_device_tagged_and_deduped_across_nodes():
    raws = [
        RawDevice(0x0000, 0x0000, "Fulcrum One Yoke", "evdev", "/dev/input/event3"),
        RawDevice(0x0000, 0x0000, "Fulcrum One Yoke", "evdev", "/dev/input/event4"),
    ]
    items = classify(raws, _catalog(YOKE))
    assert len(items) == 1
    assert items[0].catalog_id == "yoke"
    assert items[0].registered
    assert items[0].name == "Fulcrum One Yoke"  # catalog name wins
    assert items[0].paths == ["/dev/input/event3", "/dev/input/event4"]


def test_name_match_required_for_ambiguous_usb_id():
    # Same 0000:0000 USB id but a different name → NOT the yoke.
    raws = [RawDevice(0x0000, 0x0000, "USB Audio Device", "evdev", "/dev/input/event9")]
    items = classify(raws, _catalog(YOKE))
    assert len(items) == 1
    assert items[0].catalog_id is None


def test_hidraw_panel_tagged_and_its_evdev_shadow_dropped():
    raws = [
        RawDevice(0x06A3, 0x0D67, "Saitek Switch Panel", "hidraw", "/dev/hidraw2"),
        # The panel also exposes a useless evdev node — must be suppressed.
        RawDevice(0x06A3, 0x0D67, "Saitek Switch Panel", "evdev", "/dev/input/event7"),
    ]
    items = classify(raws, _catalog(PANEL))
    assert len(items) == 1
    assert items[0].transport == "hidraw"
    assert items[0].catalog_id == "switch_panel"


def test_unregistered_devices_kept_and_marked():
    raws = [
        RawDevice(0x1234, 0x5678, "Foreign Yoke", "evdev", "/dev/input/event1"),
        RawDevice(0x046D, 0x0ABA, "Logitech Headset", "hidraw", "/dev/hidraw0"),
    ]
    items = classify(raws, _catalog(YOKE, PANEL))
    assert {it.usb for it in items} == {"1234:5678", "046d:0aba"}
    assert all(not it.registered for it in items)


def test_two_distinct_zero_usb_devices_stay_separate():
    raws = [
        RawDevice(0x0000, 0x0000, "Fulcrum One Yoke", "evdev", "/dev/input/event3"),
        RawDevice(0x0000, 0x0000, "Some Audio Node", "evdev", "/dev/input/event8"),
    ]
    items = classify(raws, _catalog(YOKE))
    assert len(items) == 2
    assert _item(items, "0000:0000") is not None
    reg = [it for it in items if it.registered]
    assert len(reg) == 1 and reg[0].catalog_id == "yoke"


def test_registered_sorted_before_unregistered():
    raws = [
        RawDevice(0x1234, 0x5678, "AAA Foreign Device", "evdev", "/dev/input/event1"),
        RawDevice(0x0000, 0x0000, "Fulcrum One Yoke", "evdev", "/dev/input/event3"),
    ]
    items = classify(raws, _catalog(YOKE))
    assert [it.registered for it in items] == [True, False]
