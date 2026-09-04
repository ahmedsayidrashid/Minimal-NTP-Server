# Developer Notes

This document covers how to set things up so the NTP server actually works end-to-end. It uses my own setup (PC as the server, Raspberry Pi as the client) as a reference.

## Reference Setup

- **Server**: PC running `main.py` from this repo.
- **Client**: Raspberry Pi running `chrony` (the default NTP client/server).
- **Network**: The Pi is connected to the PC via Ethernet, with the PC's Ethernet port configured to share its network connection (acting as a router/DHCP server for the Pi).

Since this setup uses a shared connection over an Ethernet cable, the Pi's IP address can be found by running the following command from the PC:

```bash
sudo nmap -sn 10.42.0.0/24
```

This will list all devices on the subnet along with their IP addresses.

## 1. Disable chrony on the server (PC)

Most Linux systems (including the PC acting as the server here) already run `chrony` or `systemd-timesyncd` to keep their own clock in sync. Since our custom server needs to bind to UDP port 123 itself, any existing NTP daemon on that machine needs to be stopped first, otherwise the port will already be in use.

On the server (PC):

```bash
sudo systemctl stop chrony
```

This only stops it for the current session, chrony will start again on the next reboot, so you don't need to re-enable it later. If you want it to stay off across reboots too, you can additionally run `sudo systemctl disable chrony`, but that's optional.

Verify the port is free:

```bash
sudo ss -ulnp | grep 123
```

If nothing is listening on `:123`, you're good to go.

## 2. Set up a virtual environment and install dependencies

Create an isolated venv so the project's dependencies don't get installed system-wide (also better practice).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Run the script with sudo

Linux treats any port below 1024 as privileged, and NTP uses port 123 by default. Because of this, `main.py` needs to be run with elevated permissions.

`sudo` normally resets `PATH` and won't use your activated venv's Python, so you need to either call the venv's interpreter directly by path, or use `sudo -E env "PATH=$PATH"` to preserve your environment:

```bash
sudo .venv/bin/python3 main.py
```

or:

```bash
sudo -E env "PATH=$PATH" python3 main.py
```

You can also override the port (e.g. for testing without root) using `--port`/`-p`:

```bash
python3 main.py --port 12300
```

Optional flags:

- `--time` / `-t`: serve a custom time instead of the current system time (ISO 8601 or Unix timestamp).
- `NTP_CUSTOM_TIME` environment variable (see `.env.example`): same purpose as `--time`, useful for setting a default without passing a CLI arg every run.

## 4. Set up the server as a valid reference on the client (Pi)

On the client (the Raspberry Pi, or any machine running `chrony`), point chrony at the PC's IP address instead of the default pool of NTP servers.

Edit `/etc/chrony/chrony.conf` (or `/etc/chrony.conf` depending on distro) on the Pi:

```bash
sudo nano /etc/chrony/chrony.conf
```

Comment out (or remove) the default `pool`/`server` lines, and add a line pointing to the PC's IP address (found via the `nmap` command above):

For example:

```text
server 10.42.0.1 iburst prefer
```

- `iburst` speeds up the initial synchronization by sending a burst of requests.
- `prefer` tells chrony to prefer this source over any others, which is useful since our server is a "fake" stratum 1 source that isn't cross-checked against real sources.

Restart chrony on the client to pick up the change:

```bash
sudo systemctl restart chrony
```

Then verify the Pi is actually using the custom server as its source:

```bash
chronyc sources -v
chronyc tracking
```

You should see the PC's IP listed with a `*` (currently selected source) once synchronization succeeds.

## Troubleshooting

- **`PermissionError` on the server**: you forgot `sudo` (see step 2).
- **Client never syncs / source shows as unreachable**: double-check the server is actually running and bound to `0.0.0.0:123`, that no firewall is blocking UDP/123 between the two machines, and that the IP address in `chrony.conf` is correct (IPs can change if using DHCP).
- **Client rejects the fake time**: chrony is cautious about large, sudden time jumps. If testing with a custom time far from the real time, you may need `makestep` configured more permissively on the client while testing, e.g. `makestep 1.0 -1` in `chrony.conf`.
