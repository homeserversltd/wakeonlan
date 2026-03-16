# Wake on LAN Tab

**Disclaimer:** This software is provided in pre-release form "as is" and "as available," without warranty of any kind. It may not operate correctly, may corrupt or delete data, and is not intended for production use. You use it at your own risk.

Premium tab for sending Wake-on-LAN magic packets from the HOMESERVER UI. Use from phone over Tailscale for one-tap wake of workstation (or any target on the same LAN). Integrates with DHCP: show active leases and add or remove WoL targets from a single CSV.

## CSV location

Targets are stored at **premium root** (flat, one level down from tabs). Path is configurable via `backend/config.json` (infinite-index style `paths.wol_csv`).

- **Default path:** `/var/www/homeserver/premium/wakeonlan.csv`
- **Format:** header `name,mac,broadcast`, one row per target.

Create the file manually or add targets from the **DHCP Leases** section in the tab; the tab creates the file with header on first add.

## Features

- **WoL Targets:** List, Wake (one or all), Remove. Targets are persisted in `premium/wakeonlan.csv`.
- **DHCP integration:** Fetches active leases from the DHCP tab API; add any lease as a WoL target (append to CSV). Leases already in WoL targets are hidden from the “Add” list.
- **Config:** Backend uses `backend/config.json` for `paths.wol_csv` (infinite-index pattern).

## API

- `GET /api/wakeonlan/targets` — list targets from CSV
- `POST /api/wakeonlan/targets` — add target: body `{ "name", "mac", "broadcast"? }` or `{ "name", "mac", "ip" }` (broadcast derived from IP)
- `DELETE /api/wakeonlan/targets/<name>` — remove target from CSV
- `POST /api/wakeonlan/wake` — body `{"name": "workstation"}` or `{"wake_all": true}`
- `GET /api/wakeonlan/status` — status and CSV path

## Flow

1. Phone on Tailscale → open HOMESERVER UI → Wake on LAN tab.
2. Optionally add targets from **DHCP Leases** (Add as WoL Target) or remove from **WoL Targets**.
3. Tap **Wake** for a target (or **Wake all**).
4. Wait 30–60 s, then SSH from phone to the workstation (or use Cursor agent flow).

No sudo or system packages for WoL; stdlib Python (socket, csv). DHCP lease data is read from the existing DHCP tab API.
