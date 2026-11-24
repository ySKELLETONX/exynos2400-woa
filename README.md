# Native Windows research for Galaxy S24 (Exynos 2400)

An experimental fork of [ntdevlabs/exynos9810-woa](https://github.com/ntdevlabs/exynos9810-woa)
to investigate **Windows 11 ARM64 directly on the Samsung Galaxy S24 SM-S921B**
(`e1s`, Exynos 2400 / `s5e9945`). The intended end result replaces Android;
this is not a Winlator/WinXclipse configuration or a remote desktop client.

**Current status: initial research tooling. Windows does not boot on the S24
with this fork. No S24 firmware or Windows drivers are available here.**

The S9+ firmware, recovery, drivers and partition routines inherited from the
ancestor are references for a different board. Do not flash them on an S24.
The inherited installer explicitly blocks SM-S921B installation.

## Implemented

- An e1s research profile with explicit unimplemented/unknown boot milestones.
- An ADB inventory collector limited to named properties and fixed read commands.
- Exact model/codename/SoC/ABI matching, without enabling firmware installation.
- Installer regression tests that keep S24 outside the S9+ installation path.
- A porting plan and pinned source references, distinguishing reported upstream
  results from observations on the local phone.

## Start here

Read [the porting plan](docs/s24-port.md), then collect a fresh inventory on an
already authorized ADB connection:

```powershell
python tools/s24/collect.py --adb <path-to-adb.exe>
```

Reports are saved under the Git-ignored `research-artifacts/` directory.
There is no S24 flashing command or unlock automation. Inventory can proceed
on stock Android without root or rebooting.

| Item | State |
|---|---|
| Target | SM-S921B only; other S24 variants are not interchangeable |
| Hardware inventory | Collector implemented; complete live report still required |
| Bootloader unlock / stock restore | Not validated on the local firmware |
| Exynos 2400 UEFI and ACPI | Not implemented |
| Native Windows storage, USB, input and display drivers | Not implemented |
| Windows 11 boot / usable desktop | Not validated |

The first hardware milestone is a recoverable UEFI entry with diagnostics, not
a Windows installation. Bootloader restrictions and missing drivers may block
the project; success and a completion date cannot be promised.

## Sources and licensing

Source revisions and their limits are recorded in
[sources.lock.json](devices/samsung-e1s/sources.lock.json). External Linux
bring-up reports are research references, not proof of Windows compatibility.
No vendor firmware or Windows installation media is redistributed.

The original [S9+ README](README.upstream.md) is retained for historical and
build reference; its device-support statements apply only to the S9+.
Existing copyrights, [LICENSE](LICENSE), [NOTICE](NOTICE) and component-specific
licenses are preserved. New research tooling is BSD-2-Clause-Patent.

Host checks and build commands are in [docs/s24-port.md](docs/s24-port.md#validation-in-this-fork).
