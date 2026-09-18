# YubiKey FIDO2 passthrough into the `sandbox` VM

DAR-OW-158 / N17 "Provision FIDO2/USB signing into sandbox" — **Part A (USB
passthrough): done and verified 2026-09-18.** Part B (Admin-UI sign sidecar with
FIDO2 grants, in-guest) is still missing — see below.

## Why the key has to be inside the guest

The governed signing flow is `python3 OW_tools/cli/ow_sign.py --ci-id <ID>
--phase <PHASE>` (see the `operator-signatures` skill, CI 10760). `ow_sign`
performs a **WebAuthn/FIDO2 assertion with a physical button touch**; the touch is
the security property, and no software can substitute for it. `ow_sign` talks to
the authenticator through `fido2.hid.CtapHidDevice`, which on Linux reads
`/dev/hidrawN` for the FIDO HID interface (usage page `0xF1D0`) of the key.

So an in-guest closure requires, in order:

1. the YubiKey USB device attached to the `sandbox` libvirt domain (Part A),
2. a readable `/dev/hidrawN` for the seat-less SSH session that runs `ow_sign`,
3. the Admin-UI sign sidecar on `localhost:8000` plus the FIDO2 RBAC grants,
   which mint the nonce and record the assertion (Part B).

Without (1) and (2) the guest sees no FIDO device at all; without (3) `ow_sign`
fails with `Connection refused` before it can ask for a touch.

## What the host looked like before

- YubiKey 5 (`1050:0407`, "Yubikey 4/5 OTP+U2F+CCID") on host bus 5 port 2,
  three interfaces: OTP HID (iface 0), FIDO HID (iface 1), CCID (iface 2).
- The `sandbox` domain had a `qemu-xhci` controller but **no USB hostdev**, so the
  guest saw only root hubs.
- Host user `d` is in group `libvirt`, so `virsh attach-device` needs **no host
  sudo** (per DAR-158 constraint RD-3, host root stays with the operator).

## Part A — what was done

1. **Device XML** `yubikey_usb_hostdev.xml` — `<hostdev mode='subsystem'
   type='usb' managed='yes'>` matched by **vendor/product** (`0x1050`/`0x0407`)
   rather than bus/port, so the key keeps working if it moves host ports.
   `managed='yes'` makes libvirt unbind the host `usbhid` driver on attach and
   rebind it on detach.
2. **Attach** with `virsh attach-device sandbox yubikey_usb_hostdev.xml --live`
   (transient). The domain XML is **not** persisted, because a persistent USB
   hostdev makes `virsh start sandbox` fail whenever the key is unplugged.
3. **Guest udev rule** `/etc/udev/rules.d/70-yubikey-fido.rules`:

   ```
   SUBSYSTEM=="hidraw", ENV{ID_FIDO_TOKEN}=="1", MODE="0660", GROUP="plugdev"
   ```

   Stock Ubuntu only sets `TAG+="uaccess"` on the FIDO hidraw node
   (`60-fido-id.rules`). `uaccess` ACLs are granted to sessions that own a seat,
   so the SSH session that drives `ow_sign` got `EACCES` on `/dev/hidraw1`.
   User `d` is in `plugdev`, so the group grant closes that gap.
4. **Helper command** `sandbox-fido` (`~/.local/bin/sandbox-fido`):
   `status`, `check`, `on`, `off`, `persist`, `unpersist`.

## Evidence (2026-09-18)

Host, before: `virsh dumpxml sandbox | grep hostdev` → nothing.
Guest, before: `lsusb` → only root hubs; no `/dev/hidraw*`.

After `sandbox-fido on`:

```
key plugged into host   : yes
attached to sandbox    : yes (live)
  in persistent config : no (VM boots without the key)
host apps can use key  : no (handed over to the guest)
guest sees the key     : yes
    crw------- 1 root root    240, 0   /dev/hidraw0   (OTP HID, not granted)
    crw-rw---- 1 root plugdev 240, 1   /dev/hidraw1   (FIDO HID)
```

In-guest probe over the same seat-less SSH path that runs `ow_sign`:

```
FIDO transport OK: /dev/hidraw1 aaguid 2fc0579f-8113-47ea-b116-bb5a8db9202a
CTAP versions: ['U2F_V2', 'FIDO_2_0', 'FIDO_2_1_PRE']
```

That is a full CTAP2 `getInfo` round trip through the guest's `python-fido2`
2.2.1 (the version `ow_sign` requires), so discovery, permissions and the HID
transport are all proven. The probe deliberately never asks for a touch.

`sandbox-fido off` was also exercised: the key returns to the host (host FIDO
hidraw node reappears) and the guest loses it.

## Trade-offs the operator should know

- **Exclusive handover.** While the key is attached, host apps (browser
  WebAuthn, `ykman`, GitHub 2FA) cannot use it. `lsusb` still lists the device on
  the host because qemu holds it through usbfs, which is why `sandbox-fido
  status` reports host availability from the host's FIDO hidraw node instead.
- **Not persisted by default.** Live attach keeps the VM bootable when the key is
  away. `sandbox-fido persist` exists for a permanently-dedicated key, and it
  warns that `virsh start sandbox` will then fail if the key is unplugged.
- **One touch per assertion.** `ow_sign` must not be looped: the key needs a beat
  to reset between assertions, or later touches fail with `EIO` (skill, "Batch /
  Multiple Sign-offs").
- **CCID is not enabled in-guest.** OpenPGP/PIV over the CCID interface needs
  `pcscd` + `libccid` + `scdaemon` in the guest; FIDO2/WebAuthn does not, so those
  were intentionally not installed.

## Part B — still missing (blocks an in-guest closure)

Verified 2026-09-18 in the guest: `k3s` is active and the `overwatch` namespace
exists, but nothing listens on `:8000` and
`POST /api/v1/auth/nonce` fails with `curl` exit 7 (connection refused). The
guest also has no `scdaemon`/`ykman`/`pcsc-tools`, which is fine for FIDO2.

To finish N17: deploy the Admin-UI sign sidecar into the guest `overwatch`
namespace (mirroring N12's DB/gateway deploy path) and apply the FIDO2 RBAC
grants from the skill (`auth.ow_generate_nonce` EXECUTE,
`auth.fido2_challenge_state` SELECT/INSERT/DELETE, `auth.fido_credentials` SELECT,
`auth.approval_signatures` INSERT, `auth.udrs` SELECT; and keep
`audit.ow_log_signature_change` out of reach of `overwatch_agent`). Then
`ow_sign --ci-id <ID> --phase <PHASE>` in-guest completes with one button touch.

## Files

| Path | Role |
|------|------|
| `yubikey_usb_hostdev.xml` | libvirt USB hostdev definition |
| `backups/sandbox_domain_*.xml` | pre-change domain XML snapshots (not committed) |
| `~/.local/bin/sandbox-fido` | operator command: status / check / on / off / persist / unpersist |
| guest `/etc/udev/rules.d/70-yubikey-fido.rules` | plugdev access to the FIDO hidraw node |
