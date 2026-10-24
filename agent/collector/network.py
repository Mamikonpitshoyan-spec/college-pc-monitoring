"""Network interface counters, addresses, and delta-based traffic rates."""

from __future__ import annotations

import logging
import socket
from typing import Any

import psutil

from collector.rates import ByteCounters, ByteRateTracker

logger = logging.getLogger(__name__)


class NetworkCollector:
    """Collect per-interface values without assuming interface names or topology."""

    def __init__(self) -> None:
        self._rate_tracker = ByteRateTracker()

    def collect(self) -> dict[str, Any]:
        interface_addresses = psutil.net_if_addrs()
        interface_counters = psutil.net_io_counters(pernic=True)
        counter_values = {
            name: ByteCounters(int(counter.bytes_recv), int(counter.bytes_sent))
            for name, counter in interface_counters.items()
        }
        rates = self._rate_tracker.sample(counter_values)
        try:
            stats = psutil.net_if_stats()
        except OSError:
            stats = {}
        interfaces: list[dict[str, Any]] = []

        for name in sorted(set(interface_addresses) | set(interface_counters)):
            addresses = interface_addresses.get(name, [])
            counter = interface_counters.get(name)
            rate = rates.get(name)
            interfaces.append(
                {
                    "name": name,
                    "is_up": stats[name].isup if name in stats else None,
                    "primary": False,
                    "ipv4": self._addresses(addresses, socket.AF_INET),
                    "ipv6": self._addresses(addresses, socket.AF_INET6),
                    "mac": self._mac_address(addresses),
                    "rx_bytes": counter.bytes_recv if counter else None,
                    "tx_bytes": counter.bytes_sent if counter else None,
                    "rx_speed_Bps": rate.inbound_Bps if rate else None,
                    "tx_speed_Bps": rate.outbound_Bps if rate else None,
                    "packets_received": counter.packets_recv if counter else None,
                    "packets_sent": counter.packets_sent if counter else None,
                    "receive_errors": counter.errin if counter else None,
                    "send_errors": counter.errout if counter else None,
                    "receive_dropped": counter.dropin if counter else None,
                    "send_dropped": counter.dropout if counter else None,
                }
            )
        primary = self._primary_interface(interfaces)
        if primary is not None:
            primary["primary"] = True
        return {"interfaces": interfaces}

    @staticmethod
    def _primary_interface(interfaces: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Main active adapter: up, real LAN IPv4, not virtual, most traffic."""
        virtual = ("loopback", "vethernet", "virtualbox", "vmware", "hyper-v", "bluetooth",
                   "teredo", "isatap", "wsl", "docker", "vpn", "npcap", "tap-", "tun")

        def usable(iface: dict[str, Any]) -> bool:
            ips = [ip for ip in iface.get("ipv4") or [] if not ip.startswith(("127.", "169.254."))]
            name = (iface.get("name") or "").lower()
            return bool(ips) and iface.get("is_up") is not False and not any(v in name for v in virtual)

        candidates = [iface for iface in interfaces if usable(iface)]
        if not candidates:
            return None
        return max(candidates, key=lambda i: (i.get("rx_bytes") or 0) + (i.get("tx_bytes") or 0))

    @staticmethod
    def _addresses(addresses: list[Any], family: int) -> list[str] | None:
        values = [address.address for address in addresses if address.family == family]
        return values or None

    @staticmethod
    def _mac_address(addresses: list[Any]) -> str | None:
        link_family = getattr(psutil, "AF_LINK", None)
        for address in addresses:
            if link_family is not None and address.family == link_family:
                return address.address or None
        return None


class PortsCollector:
    """Listening (open) TCP/UDP ports with the owning program name."""

    def collect(self) -> dict[str, Any]:
        try:
            connections = psutil.net_connections(kind="inet")
        except (psutil.AccessDenied, OSError) as error:
            logger.info("Listening ports are unavailable: %s", error)
            return {"listening": None}
        names: dict[int, str | None] = {}
        seen: set[tuple] = set()
        listening: list[dict[str, Any]] = []
        for conn in connections:
            is_tcp_listen = conn.type == socket.SOCK_STREAM and conn.status == psutil.CONN_LISTEN
            is_udp = conn.type == socket.SOCK_DGRAM
            if not conn.laddr or not (is_tcp_listen or is_udp):
                continue
            protocol = "TCP" if is_tcp_listen else "UDP"
            key = (protocol, conn.laddr.ip, conn.laddr.port, conn.pid)
            if key in seen:
                continue
            seen.add(key)
            if conn.pid and conn.pid not in names:
                try:
                    names[conn.pid] = psutil.Process(conn.pid).name()
                except (psutil.Error, OSError):
                    names[conn.pid] = None
            listening.append({
                "protocol": protocol,
                "address": conn.laddr.ip,
                "port": conn.laddr.port,
                "pid": conn.pid,
                "process": names.get(conn.pid) if conn.pid else None,
            })
        listening.sort(key=lambda item: (item["protocol"], item["port"]))
        return {"listening": listening}
