from system_pet.guard import (Detector, Finding, Listener, Throttle, load_known_devices, parse_arp_a,
                              parse_proc_net_arp, save_known_devices)

PROC_ARP = """IP address       HW type     Flags       HW address            Mask     Device
192.168.0.1      0x1         0x2         9c:A2:f4:ad:e1:71     *        wlan0
192.168.0.50     0x1         0x0         00:00:00:00:00:00     *        wlan0
192.168.0.7      0x1         0x2         11:22:33:44:55:66     *        wlan0
"""

WIN_ARP = """
Interface: 192.168.1.20 --- 0x7
  Internet Address      Physical Address      Type
  192.168.1.1           aa-bb-cc-dd-ee-ff     dynamic
  192.168.1.40          00-11-22-33-44-55     dynamic
  192.168.1.255         ff-ff-ff-ff-ff-ff     static
  224.0.0.22            01-00-5e-00-00-16     static
  255.255.255.255       ff-ff-ff-ff-ff-ff     static
"""


def test_parse_proc_net_arp_skips_incomplete_and_normalises_mac():
    assert parse_proc_net_arp(PROC_ARP) == {"9c:a2:f4:ad:e1:71": "192.168.0.1",
                                            "11:22:33:44:55:66": "192.168.0.7"}


def test_parse_arp_a_windows_skips_broadcast_and_multicast():
    assert parse_arp_a(WIN_ARP) == {"aa:bb:cc:dd:ee:ff": "192.168.1.1",
                                    "00:11:22:33:44:55": "192.168.1.40"}


def test_parsers_tolerate_garbage():
    assert parse_proc_net_arp("") == {}
    assert parse_arp_a("No ARP Entries Found.") == {}


def L(port, name="python3", local=True):
    return Listener(port, name, local)


def test_first_scan_is_silent_baseline():
    d = Detector()
    assert d.scan({"aa:aa:aa:aa:aa:aa": "10.0.0.2"}, {80: L(80)}) == []
    assert d.devices == {"aa:aa:aa:aa:aa:aa": "10.0.0.2"} and d.ports == {80}


def test_new_port_and_device_are_reported_after_baseline():
    d = Detector()
    d.scan({"aa:aa:aa:aa:aa:aa": "10.0.0.2"}, {80: L(80)})
    out = d.scan({"aa:aa:aa:aa:aa:aa": "10.0.0.2", "bb:bb:bb:bb:bb:bb": "10.0.0.9"},
                 {80: L(80), 8765: L(8765, "python3", local=False)})
    kinds = sorted(f.kind for f in out)
    assert kinds == ["device", "port"]
    text = " ".join(f.text for f in out)
    assert "10.0.0.9" in text and "8765" in text and "reachable from your network" in text


def test_same_finding_is_not_repeated():
    d = Detector()
    d.scan({}, {80: L(80)})
    assert len(d.scan({}, {80: L(80), 9000: L(9000)})) == 1
    assert d.scan({}, {80: L(80), 9000: L(9000)}) == []
    assert d.scan({}, {80: L(80)}) == []                       # closed...
    assert d.scan({}, {80: L(80), 9000: L(9000)}) == []        # ...and reopened: already known


def test_known_devices_from_disk_alert_on_new_mac():
    d = Detector({"aa:aa:aa:aa:aa:aa": "10.0.0.2"})
    out = d.scan({"aa:aa:aa:aa:aa:aa": "10.0.0.2", "cc:cc:cc:cc:cc:cc": "10.0.0.5"}, {})
    assert [f.kind for f in out] == ["device"]


def test_disabled_watchers_do_nothing():
    d = Detector()
    d.scan({}, {80: L(80)}, want_devices=False, want_ports=False)
    assert d.ports is None and d.devices == {}


def test_throttle_merges_and_spaces_alerts():
    t = Throttle()
    one = [Finding("port", "New listener on port 1")]
    assert t.offer(one, 100.0) == "New listener on port 1"
    assert t.offer(one, 105.0) is None                        # too soon, kept pending
    msg = t.offer([Finding("port", "New listener on port 2")], 130.0)
    assert msg.startswith("2 new things detected") and "port 1" in msg
    assert t.offer([], 200.0) is None


def test_known_devices_roundtrip(tmp_path):
    assert load_known_devices() == {}
    save_known_devices({"aa:aa:aa:aa:aa:aa": "10.0.0.2"})
    assert load_known_devices() == {"aa:aa:aa:aa:aa:aa": "10.0.0.2"}
