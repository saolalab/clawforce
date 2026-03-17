"""URL/request security policy — SSRF protection for network tools."""

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlparse

IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address
IPNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network

_DEFAULT_BLOCKED_CIDR_TEXT = (
    "0.0.0.0/8",
    "10.0.0.0/8",
    "100.64.0.0/10",
    "127.0.0.0/8",
    "169.254.0.0/16",
    "172.16.0.0/12",
    "192.0.0.0/24",
    "192.0.2.0/24",
    "192.88.99.0/24",
    "192.168.0.0/16",
    "198.18.0.0/15",
    "198.51.100.0/24",
    "203.0.113.0/24",
    "224.0.0.0/4",
    "240.0.0.0/4",
    "::/128",
    "::1/128",
    "fc00::/7",
    "fe80::/10",
)


def _parse_cidrs(items: tuple[str, ...]) -> tuple[IPNetwork, ...]:
    networks: list[IPNetwork] = []
    seen: set[str] = set()
    for text in items:
        text = (text or "").strip()
        if not text:
            continue
        try:
            network = ipaddress.ip_network(text, strict=False)
        except ValueError:
            continue
        key = str(network)
        if key in seen:
            continue
        seen.add(key)
        networks.append(network)
    return tuple(networks)


_DEFAULT_BLOCKED_NETWORKS = _parse_cidrs(tuple(_DEFAULT_BLOCKED_CIDR_TEXT))


def _host_matches_allowlist(host: str, allowlist: tuple[str, ...]) -> bool:
    if not allowlist:
        return True
    lowered = host.lower()
    for token in allowlist:
        t = token.lower().strip()
        if not t:
            continue
        if lowered == t:
            return True
        if lowered.endswith(f".{t}"):
            return True
    return False


def _is_local_host(host: str) -> bool:
    lowered = host.lower()
    if lowered == "localhost" or lowered.endswith(".local"):
        return True
    return False


def _parse_host_ip(host: str) -> IPAddress | None:
    try:
        return ipaddress.ip_address(host)
    except ValueError:
        return None


def _ip_in_blocked_cidrs(ip: IPAddress, blocked_cidrs: tuple[IPNetwork, ...]) -> bool:
    return any(ip in network for network in blocked_cidrs)


def _resolve_host_ips(host: str) -> tuple[IPAddress, ...]:
    resolved: list[IPAddress] = []
    seen: set[str] = set()
    for _, _, _, _, sockaddr in socket.getaddrinfo(host, None):
        if not sockaddr:
            continue
        candidate = str(sockaddr[0] or "").strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        try:
            resolved.append(ipaddress.ip_address(candidate))
        except ValueError:
            continue
    return tuple(resolved)


@dataclass(frozen=True)
class NetworkSecurityPolicy:
    """SSRF/private-network guard for URLs used by network tools (web_fetch, etc.)."""

    allow_private_network: bool = False
    request_allowlist: tuple[str, ...] = ()
    request_blocked_cidrs: tuple[IPNetwork, ...] = ()
    check_dns_private_hosts: bool = True
    dns_fail_closed: bool = False

    def validate_request_url(self, url: str) -> tuple[bool, str | None]:
        """Return (True, None) if the URL is allowed, else (False, error_message)."""
        parsed = urlparse(str(url or "").strip())
        scheme = (parsed.scheme or "").lower()
        if scheme not in {"http", "https"}:
            return False, "Only http(s) URLs are allowed."

        host = (parsed.hostname or "").strip().lower()
        if not host:
            return False, "Request URL must include a valid hostname."

        if self.request_allowlist and not _host_matches_allowlist(host, self.request_allowlist):
            return (
                False,
                f"Request URL host is not in the allowlist ({', '.join(self.request_allowlist)}).",
            )

        if self.allow_private_network:
            return True, None

        blocked_cidrs = self.request_blocked_cidrs or _DEFAULT_BLOCKED_NETWORKS

        if _is_local_host(host):
            return (
                False,
                "Private/local network targets are blocked (SSRF protection).",
            )

        host_ip = _parse_host_ip(host)
        if host_ip is not None and _ip_in_blocked_cidrs(host_ip, blocked_cidrs):
            return (
                False,
                "Private/local network targets are blocked (SSRF protection).",
            )

        if self.check_dns_private_hosts:
            try:
                resolved_ips = _resolve_host_ips(host)
            except OSError:
                if self.dns_fail_closed:
                    return False, "DNS resolution failed for request host."
                resolved_ips = ()
            if not resolved_ips and self.dns_fail_closed:
                return False, "DNS resolution produced no addresses for request host."
            for resolved in resolved_ips:
                if _ip_in_blocked_cidrs(resolved, blocked_cidrs):
                    return (
                        False,
                        f"Request host resolves to a private/local address ({resolved}).",
                    )

        return True, None
