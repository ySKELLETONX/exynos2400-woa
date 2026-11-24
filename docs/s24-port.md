# Galaxy S24 native Windows port

Target: **SM-S921B / e1s / Exynos 2400 (s5e9945)**. Status: research only.
No S24 UEFI image, Windows boot, driver package or recovery path has been
validated by this fork. The original installer remains an S9+ installer and
explicitly rejects the S24, even if passed a custom target list.

## Current evidence

The allowlisted collector ran successfully on the local phone on 2026-11-24.
The raw observation remains local under `research-artifacts/`; no transport
identifier, account data or partition contents are published.

| Observation | Value |
|---|---|
| Model / codename | SM-S921B / e1s |
| SoC / board / ABI | s5e9945 / erd9945 / arm64-v8a |
| Bootloader and incremental build | S921BXXUHEZIF |
| Android / SDK | 17 / 37 |
| Security patch | 2026-09-05 |
| Kernel | 6.1.162-android14-11 |
| Physical display size | 1080 x 2340 |
| Flash lock / vbmeta state | 1 / locked |
| Verified boot / warranty bit | green / 0 |
| OEM-unlock permission/support properties | Unavailable, not proof of either supported or unsupported unlocking |
| Device-tree model / compatible | Unavailable to the unprivileged ADB collector |

The partition directory exposes `boot`, `init_boot`, `vendor_boot`, `dtbo`,
`recovery`, `vbmeta`, `vbmeta_system` and `super`, among others. Directory names
do not establish partition geometry, slot policy or a safe write target.
There is no memory map or firmware-matched device tree yet.

### Boot-access research

The first blocking hardware prerequisite is a confirmed path to boot custom
code with a tested stock restore procedure. Two open upstream reports refer to
this exact firmware: [Root-My-Galaxy #796](https://github.com/BuSung-dev/Root-My-Galaxy/issues/796)
and [Root-My-Galaxy-Payloads #453](https://github.com/BuSung-dev/Root-My-Galaxy-Payloads/issues/453).
They are requests/reports about Android root, not demonstrations of an unlocked
bootloader or native Windows. As reviewed on 2026-11-24, #453 has no comments;
#796's comment requests a different build. Neither establishes boot access here.

A [maintainer's explanation on another Samsung variant](https://github.com/rushiranpise/Root-My-Galaxy-Next/issues/52#issuecomment-6588311278)
distinguishes a visible OEM-unlock toggle from an actual bootloader unlock.
That discussion concerns SM-S928B and cannot prove the Exynos SM-S921B's
bootloader implementation. It does rule out treating a runtime property edit
as sufficient evidence. No exploit, property edit, unlock, reboot or partition
write was attempted during this inventory.

The external postmarketOS project reports Linux on this model using stock
Samsung kernel/modules and a replacement `init_boot` ramdisk. Its documented
reference firmware is **S921BXXU6BYE7 / Android 15**. It retains Android HAL
processes for some peripherals. This provides research leads; Windows cannot
use Linux kernel modules or Android HAL services as native Windows drivers.
See the pinned sources in `devices/samsung-e1s/sources.lock.json`.

## Collect evidence without changing the phone

Enable ADB on an already authorized USB or wireless connection, then run from
the repository root:

```powershell
python tools/s24/collect.py --adb <path-to-adb.exe>
```

With multiple devices, add `--serial <adb-transport>`. The script issues only
named `getprop` reads and the fixed read commands in `OBSERVATIONS`. It does
not pair, connect, reboot, request root, change properties or read partition
contents. It records unavailable reads rather than escalating privileges.
It requires exact model, codename, chipset token and ABI matches before reporting
the target identity as confirmed. Lock properties remain observations, not a
claim that unlocking is possible.

The default report is `research-artifacts/s24-inventory.json`, ignored by Git.
Serial, IMEI, account data, wireless address and pairing credentials are not
collected. Review any report before sharing it. Existing evidence is never
overwritten; specify a different `--out` path for a new observation.

## Implementation sequence and acceptance evidence

| Milestone | Work | Evidence needed before advancing |
|---|---|---|
| Inventory | Exact bootloader/firmware, lock state, model, SoC, ABI, kernel, partition names | Fresh local report; unknown values stay unknown |
| Boot access and recovery | Determine whether this firmware permits a documented unlock and whether stock recovery is available | Exact stock package, hashes, backup plan and confirmed recovery procedure; unlocking is a separate destructive operation |
| Hardware description | Obtain firmware-matched DTB/DTBO and source references | Reserved memory, RAM, interrupt controller, timer, display, UFS, USB, IOMMU, watchdog and power dependencies traced to sources |
| UEFI entry | Implement a new E1sPkg and Exynos2400Pkg | Entry/exception level, cache/MMU state, memory reservations and a recoverable diagnostic heartbeat on e1s |
| UEFI services | Implement memory map, GOP, storage path, ACPI, timer, reset and runtime services | Repeatable UEFI operation and Windows loader diagnostics |
| Windows minimum boot | Develop native drivers for required controllers and handoff | Exact ARM64 build reaches kernel with repeatable logs; no borrowed S9 offsets |
| Usable desktop | Input, storage, USB, display/power management; later Wi-Fi/audio/GPU/modem | Per-device tests on the exact board and firmware |
| Installer | Integrate an e1s-only recovery, partition plan and artifact catalog | Backup/restore and clean end-to-end installation validated on the target |

`profile.json` deliberately leaves the UEFI platform, driver package and tested
Windows builds empty. There is no flash override. Reaching Windows is not
guaranteed: bootloader access and missing Windows drivers may prevent it.

## What can be reused from the ancestor

Host process management, log redaction, image preparation abstractions, checksums,
backup verification and installer tests are candidates for reuse. The following
must be implemented or proven for e1s rather than renamed:

| Area | Ancestor implementation | Required e1s work |
|---|---|---|
| Platform entry / RAM | `firmware/Platform/Star2LtePkg` | New board memory map, reserved regions and entry contract |
| Serial / PMU | `firmware/Silicon/Exynos9810Pkg` | Exynos 2400 register descriptions and clock/power dependencies |
| Display | S9+ fixed framebuffer assumptions | e1s panel/scanout handoff and GOP, then native display support |
| UFS | `drivers/Exynos9810Ufs` | Controller/PHY/DMA/IOMMU compatibility investigation and new driver as needed |
| Input | S9+ HSI2C and S6SY761 touch drivers | Identify actual e1s controller, transport, interrupt and power sequence |
| ACPI | `Star2LtePkg/AcpiTables` | Rebuild processor topology, GIC, timer, device resources and dependencies |
| Recovery / partitions | star2lte recovery and partition rules | Firmware-matched e1s recovery/partition discovery and restore proof |

Do not flash the ancestor's `.img` files, reuse its partition numbers, assume an
Android property is an OEM-unlock guarantee, or downgrade firmware using another
model's procedure. The external Linux project's notes include a GPIO debug read
that reportedly panics the phone; the collector does not probe debugfs or MMIO.

## Validation in this fork

```powershell
python -m pytest -q tools/s24/tests tools/release/tests
python tools/release/scan.py
dotnet test installer/tests/S9Woa.Installer.Core.Tests/S9Woa.Installer.Core.Tests.csproj -p:Platform=x64 -c Release --nologo
dotnet build installer/src/S9Woa.Installer.App/S9Woa.Installer.App.csproj -p:Platform=x64 -c Release --nologo
```

Host tests validate collection and rejection of unsupported installations. They
do not validate firmware or native Windows execution on the S24.
