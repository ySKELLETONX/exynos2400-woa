#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Collect an allowlisted S24 inventory over an already authorized ADB transport.

Does not pair, connect, reboot, elevate, write to the phone or read partitions.
An inventory is evidence for research, never permission to flash.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / "devices" / "samsung-e1s" / "profile.json"
PROPERTIES = (
    "ro.product.model", "ro.boot.em.model", "ro.product.device",
    "ro.product.vendor.device", "ro.soc.model", "ro.board.platform",
    "ro.hardware", "ro.boot.hardware", "ro.product.cpu.abi",
    "ro.bootloader", "ro.build.version.release", "ro.build.version.sdk",
    "ro.build.version.security_patch", "ro.build.version.incremental",
    "ro.boot.flash.locked", "ro.boot.vbmeta.device_state",
    "ro.boot.verifiedbootstate", "sys.oem_unlock_allowed",
    "ro.oem_unlock_supported", "ro.boot.warranty_bit",
)
OBSERVATIONS = {
    "kernel": ("uname", "-r"),
    "memory": ("cat", "/proc/meminfo"),
    "display": ("wm", "size"),
    "partition_names": ("ls", "/dev/block/by-name"),
    "device_tree_model": ("cat", "/sys/firmware/devicetree/base/model"),
    "device_tree_compatible": ("cat", "/sys/firmware/devicetree/base/compatible"),
}


def adb(adb_path: str, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run([adb_path, *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=20, check=False)


def select_device(output: str, serial: str | None) -> str:
    devices = [line.split()[:2] for line in output.splitlines()
               if line.strip() and not line.startswith(("List of devices", "*"))]
    devices = [row for row in devices if len(row) == 2]
    if serial is not None:
        if [serial, "device"] not in devices:
            raise ValueError("Selected transport is absent, offline or unauthorized.")
        return serial
    ready = [row[0] for row in devices if row[1] == "device"]
    if len(ready) != 1:
        raise ValueError("Exactly one authorized device is required; otherwise use --serial.")
    return ready[0]


def assess(props: dict[str, str], profile: dict) -> dict:
    model = props.get("ro.boot.em.model") or props.get("ro.product.model", "")
    codename = props.get("ro.product.device") or props.get("ro.product.vendor.device", "")
    soc_values = [props.get(key, "").lower() for key in
                  ("ro.soc.model", "ro.board.platform", "ro.hardware", "ro.boot.hardware")]
    matches = {
        "model": model.upper() == profile["model"],
        "codename": codename.lower() == profile["codename"],
        "soc": any(value in profile["soc_tokens"] for value in soc_values),
        "architecture": props.get("ro.product.cpu.abi") == profile["architecture"],
    }
    flash_locked = props.get("ro.boot.flash.locked")
    return {
        "identity_matches": matches,
        "target_matches": all(matches.values()),
        "flash_lock_observation": {"1": "locked", "0": "unlocked"}.get(flash_locked, "unknown"),
        "oem_unlock_allowed_observation": {"1": True, "0": False}.get(props.get("sys.oem_unlock_allowed")),
        "boot_access_validated": False,
        "windows_boot_validated": False,
        "flash_allowed": False,
        "reason": "Research only: no E1sPkg UEFI or Exynos 2400 Windows driver package has been validated. "
                  "ADB properties do not prove that this firmware permits bootloader unlocking.",
    }


def collect(adb_path: str, serial: str, profile: dict) -> dict:
    props = {}
    unavailable = []
    for key in PROPERTIES:
        result = adb(adb_path, ["-s", serial, "shell", "getprop", key])
        if result.returncode == 0 and result.stdout.strip():
            props[key] = result.stdout.strip()
        else:
            unavailable.append(key)
    observations = {}
    for label, command in OBSERVATIONS.items():
        result = adb(adb_path, ["-s", serial, "shell", *command])
        observations[label] = {
            "status": "observed" if result.returncode == 0 and result.stdout.strip() else "unavailable",
            "value": result.stdout.strip().replace("\0", "\n") if result.returncode == 0 else None,
        }
    return {
        "schema_version": 1,
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "profile_sha256": hashlib.sha256(PROFILE.read_bytes()).hexdigest(),
        "properties": props,
        "unavailable_properties": unavailable,
        "observations": observations,
        "assessment": assess(props, profile),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", default="adb", help="Path to Android platform-tools adb")
    parser.add_argument("--serial", help="Already connected ADB transport; not included in report")
    parser.add_argument("--out", type=Path, default=ROOT / "research-artifacts" / "s24-inventory.json")
    args = parser.parse_args(argv)
    try:
        if args.out.exists():
            raise ValueError("Output already exists; choose a new --out file to preserve observations.")
        listing = adb(args.adb, ["devices"])
        if listing.returncode != 0:
            raise ValueError("ADB could not list devices.")
        serial = select_device(listing.stdout, args.serial)
        profile = json.loads(PROFILE.read_text(encoding="utf-8"))
        report = collect(args.adb, serial, profile)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        print("Inventory saved. Target identity: " + ("matched" if report["assessment"]["target_matches"] else "unconfirmed/mismatched"))
        print("Windows installation: blocked (research only).")
        return 0 if report["assessment"]["target_matches"] else 2
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        # Do not echo an exception containing the transport identifier or raw ADB output.
        message = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
        print("Inventory failed: " + message, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
