# Moen Flo Node Server — configuration

**Start here.** Setup guide for monitoring Flo by Moen smart water shutoff devices.

---

## Prerequisites

1. A **Moen Flo** account (same email/password as the [Flo by Moen](https://www.moen.com/flo) mobile app).
2. At least one **Smart Water Shutoff** registered in your Flo account.
3. Polyglot v3 on Polisy or eISY with outbound HTTPS to `api.meetflo.com`.

This integration uses the community [aioflo](https://github.com/bachya/aioflo) library (not an official Moen API).

---

## Quick start

1. Add **Moen Flo** from the PG3 store and start the Node Server.
2. Open **Configuration** → **Custom Configuration Parameters**.
3. Set:
   - **`username`** — your Flo account email
   - **`password`** — your Flo account password
4. **Save** configuration.
5. On the **Moen Flo Controller** node:
   - **Authorization Status** should become **Authorized** (`2`)
   - **Device Count** should match your shutoff count
6. Shutoff nodes appear automatically (one per device). If not, run **Discover** on the controller.

---

## Custom Configuration Parameters

| Parameter | Description |
|-----------|-------------|
| `username` | Flo account email address |
| `password` | Flo account password |

Credentials are stored in PG3 custom params (same as other cloud Node Servers). Use a dedicated Flo account if you prefer not to share your primary credentials.

---

## Verify success

On the **Moen Flo Controller** node:

| Status | Good value | Meaning |
|--------|------------|---------|
| **Authorization Status** | `2` (Authorized) | Cloud login succeeded |
| **Device Count** | ≥ 1 | Shutoff devices discovered |

On each **Moen Flo Shutoff** node:

| Status | Meaning |
|--------|---------|
| **Valve** | `Open` or `Closed` (primary status) |
| **Cloud Connected** | Device reachable in Flo cloud |
| **Flow Rate** | Current GPM (instant rate from Flo) |
| **Pressure** | PSI |
| **Water Temperature** | Degrees F |
| **Mode** | `Home`, `Away`, or `Sleep` |
| **Daily Gallons** | Gallons used today (location total from Flo) |
| **Hourly Gallons** | Gallons used in the current hour |
| **Telemetry Age** | Minutes since Flo last updated flow/pressure/temp |

**Daily Gallons** / **Hourly Gallons** are location-level Flo totals. If you have multiple shutoffs at one location, each node shows the same location usage.

---

## Commands

Available on each shutoff node in IoX:

| Command | Action |
|---------|--------|
| **Query** | Presence ping, then refresh all status (including usage) from Flo cloud |
| **Set Valve** | Selector: Closed or Open |
| **Run Health Test** | Start a Flo health test |
| **Set Mode** | Selector: Home, Away, or Sleep |

**Caution:** Closing the valve stops water to the home. Test carefully.

---

## Troubleshooting

| Symptom | What to check |
|---------|----------------|
| Authorization stays **Failed** (`3`) | Email/password; Flo app login works; PG3 has internet |
| **Device Count** is 0 | Run **Discover**; confirm shutoff in Flo app |
| **Valve** stuck or wrong | Run **Query**; check Flo app valve state |
| **Flow Rate** stuck / high **Telemetry Age** | Run **Query**; confirm device online in Flo app; check WiFi |
| **Daily Gallons** stays 0 | Confirm usage in Flo app; wait for next short poll |
| Notice `auth` | Invalid credentials or Flo API error |

**Logs:** `logs/debug.log` in the plugin directory.

---

## Polling

Device status is refreshed from the Flo cloud on each **short poll**. The controller heartbeat runs on **long poll** only.

Each short poll (and each **Query**):

1. Sends a Flo **presence ping** so the cloud asks devices for fresh telemetry
2. Refreshes each shutoff (`device.get_info`)
3. Fetches today's water consumption once per Flo location (shared by shutoffs at that location)

Configure intervals in the PG3 Node Server UI under **Configuration → Advanced Configuration**:

| Setting | Role in this plugin |
|---------|---------------------|
| **shortPoll** | Presence ping + refresh all shutoff nodes + daily/hourly gallons |
| **longPoll** | Controller heartbeat (DON/DOF on ST) |

**Do not set shortPoll below 60 seconds.** Each short poll calls the Flo API (presence + one `get_info` per shutoff + one consumption call per location). Values under 60 increase cloud traffic and can contribute to auth or API errors. The PG3 default shortPoll is 60.

If you need a snapshot sooner, use **Query** on a shutoff or controller node instead of lowering shortPoll.
