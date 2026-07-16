#!/usr/bin/env bash
# Wi-Fi connectivity watchdog for the Pi.
#
# Symptom this exists for: the BCM43430 (brcmfmac) stack occasionally stops
# passing traffic while still reporting a healthy association — signal is fine
# (-33 dBm), the link looks "Connected", but nothing routes. Only a reconnect,
# a driver reload, or a reboot brings it back, which meant rebooting by hand.
#
# It logs to a PERSISTENT file on purpose: when the Pi is off the network you
# can't reach it over Pi Connect to read journald (which is volatile here), so
# the file is the only way to see what failed first — Wi-Fi, DHCP, DNS, or the
# upstream link.
#
# Escalates one step per run (every 2 min via netwatch.timer), resetting as
# soon as connectivity returns:
#   1st fail -> reconnect wlan0        2nd -> restart NetworkManager
#   3rd      -> reload brcmfmac        4th+ -> reboot (last resort)

set -uo pipefail

LOG=/var/log/netwatch.log
STATE=/var/lib/netwatch.fails
IFACE=wlan0
PROBE=1.1.1.1
DNS_NAME=cloudflare.com

log() { printf '%s %s\n' "$(date '+%F %T')" "$*" >> "$LOG"; }

# keep the log bounded so it never eats the SD card
if [ -f "$LOG" ] && [ "$(stat -c%s "$LOG" 2>/dev/null || echo 0)" -gt 1000000 ]; then
    tail -n 2000 "$LOG" > "$LOG.tmp" 2>/dev/null && mv "$LOG.tmp" "$LOG"
fi

gw=$(ip route | awk '/^default/ {print $3; exit}')

lan_ok=0; net_ok=0; dns_ok=0
[ -n "$gw" ] && ping -c1 -W3 "$gw"    >/dev/null 2>&1 && lan_ok=1
ping -c1 -W3 "$PROBE"                 >/dev/null 2>&1 && net_ok=1
getent hosts "$DNS_NAME"              >/dev/null 2>&1 && dns_ok=1

# Internet reachable -> healthy. Clear any failure streak.
if [ "$net_ok" = 1 ]; then
    if [ -s "$STATE" ]; then
        log "RECOVERED after $(cat "$STATE") consecutive failure(s)"
        : > "$STATE"
    fi
    exit 0
fi

fails=$(( $(cat "$STATE" 2>/dev/null || echo 0) + 1 ))
echo "$fails" > "$STATE"

# Snapshot the state at the moment of failure — this is the evidence we want.
ipaddr=$(ip -4 -o addr show "$IFACE" 2>/dev/null | awk '{print $4}')
assoc=$(iw dev "$IFACE" link 2>/dev/null | head -1)
sig=$(iw dev "$IFACE" link 2>/dev/null | awk '/signal:/ {print $2 $3}')
log "FAIL#$fails lan=$lan_ok net=$net_ok dns=$dns_ok ip=${ipaddr:-none} gw=${gw:-none} sig=${sig:-none} assoc=${assoc:-none}"

case "$fails" in
    1)
        log "  action: reconnect $IFACE"
        nmcli device disconnect "$IFACE" >/dev/null 2>&1
        sleep 3
        nmcli device connect "$IFACE" >/dev/null 2>&1
        ;;
    2)
        log "  action: restart NetworkManager"
        systemctl restart NetworkManager >/dev/null 2>&1
        ;;
    3)
        log "  action: reload brcmfmac driver"
        modprobe -r brcmfmac >/dev/null 2>&1
        sleep 3
        modprobe brcmfmac >/dev/null 2>&1
        sleep 5
        nmcli device connect "$IFACE" >/dev/null 2>&1
        ;;
    *)
        log "  action: REBOOT (last resort, $fails consecutive failures)"
        : > "$STATE"
        sync
        sleep 2
        /sbin/reboot
        ;;
esac
