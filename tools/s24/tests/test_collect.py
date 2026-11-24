# SPDX-License-Identifier: BSD-2-Clause-Patent
import importlib.util
import json
from pathlib import Path
import subprocess
from unittest.mock import patch

import pytest

SPEC = importlib.util.spec_from_file_location("s24_collect", Path(__file__).parents[1] / "collect.py")
collector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collector)
PROFILE = json.loads(collector.PROFILE.read_text(encoding="utf-8"))


def identity():
    return {"ro.product.model": "SM-S921B", "ro.product.device": "e1s",
            "ro.soc.model": "s5e9945", "ro.product.cpu.abi": "arm64-v8a",
            "ro.boot.flash.locked": "1"}


@pytest.mark.parametrize("key,value", [
    ("ro.product.model", "SM-S928B"), ("ro.product.model", "SM-S921U"),
    ("ro.product.device", "e2s"), ("ro.soc.model", "sm8650"),
    ("ro.soc.model", "prefix-s5e9945-suffix"), ("ro.product.cpu.abi", "armeabi-v7a"),
    ("ro.soc.model", ""),
])
def test_does_not_confuse_other_phones_or_missing_identity_with_s24(key, value):
    props = identity()
    props[key] = value
    assert not collector.assess(props, PROFILE)["target_matches"]


def test_even_an_unlocked_matching_phone_is_not_flashable():
    props = identity()
    props.update({"ro.boot.flash.locked": "0", "sys.oem_unlock_allowed": "1"})
    result = collector.assess(props, PROFILE)
    assert result["target_matches"]
    assert result["flash_lock_observation"] == "unlocked"
    assert not result["flash_allowed"]
    assert not result["boot_access_validated"]
    assert not result["windows_boot_validated"]
    assert collector.assess({}, PROFILE)["flash_lock_observation"] == "unknown"


def test_select_device_requires_unambiguous_authorized_transport():
    listing = "List of devices attached\nTEST-A device\nTEST-B unauthorized\n"
    assert collector.select_device(listing, None) == "TEST-A"
    with pytest.raises(ValueError):
        collector.select_device(listing, "TEST-B")
    with pytest.raises(ValueError):
        collector.select_device(listing + "TEST-C device\n", None)
    with pytest.raises(ValueError):
        collector.select_device("List of devices attached\n", None)


def test_inventory_uses_only_allowlisted_reads_and_omits_transport():
    calls = []

    def run(_path, args):
        calls.append(args)
        if args[3] == "getprop":
            assert len(args) == 5
            assert args[4] in collector.PROPERTIES
            return subprocess.CompletedProcess(args, 0, identity().get(args[4], ""), "")
        assert tuple(args[3:]) in collector.OBSERVATIONS.values()
        return subprocess.CompletedProcess(args, 1, "", "Permission denied")

    with patch.object(collector, "adb", side_effect=run):
        report = collector.collect("adb", "LOCAL-TRANSPORT-ONLY", PROFILE)
    assert report["assessment"]["target_matches"]
    assert "LOCAL-TRANSPORT-ONLY" not in json.dumps(report)
    assert all(call[:3] == ["-s", "LOCAL-TRANSPORT-ONLY", "shell"] for call in calls)
    assert report["observations"]["partition_names"]["status"] == "unavailable"
    assert report["observations"]["partition_names"]["value"] is None


def test_existing_evidence_is_not_overwritten(tmp_path):
    output = tmp_path / "inventory.json"
    output.write_text("original", encoding="utf-8")
    with patch.object(collector, "adb") as run:
        assert collector.main(["--out", str(output)]) == 1
        run.assert_not_called()
    assert output.read_text(encoding="utf-8") == "original"


def test_adb_is_invoked_as_argument_vector_without_host_shell():
    with patch.object(collector.subprocess, "run") as run:
        collector.adb("adb", ["devices"])
    args, kwargs = run.call_args
    assert args[0] == ["adb", "devices"]
    assert not kwargs.get("shell", False)
    assert kwargs["timeout"] == 20
