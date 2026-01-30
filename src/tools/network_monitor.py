"""
Network Monitor - Monitorização de Conexões de Rede
Detecta conexões suspeitas e sugere IPs para bloquear
"""

import subprocess
import re
from typing import List, Dict, Any, Optional
from collections import defaultdict
from datetime import datetime


class NetworkMonitor:
    """
    Monitor de rede que analisa conexões ativas.
    Ajuda o agente a identificar IPs suspeitos.
    """

    # Portas conhecidas por serem usadas em ataques
    SUSPICIOUS_PORTS = {
        22: "SSH (possível brute force)",
        23: "Telnet (inseguro)",
        445: "SMB (ransomware)",
        3389: "RDP (acesso remoto)",
        4444: "Metasploit default",
        5555: "Android ADB",
        6666: "IRC botnet",
        6667: "IRC botnet",
        31337: "Back Orifice"
    }

    # IPs privados (não devem ser bloqueados)
    PRIVATE_RANGES = [
        (r'^127\.', "localhost"),
        (r'^10\.', "rede privada"),
        (r'^172\.(1[6-9]|2[0-9]|3[0-1])\.', "rede privada"),
        (r'^192\.168\.', "rede privada"),
        (r'^0\.0\.0\.0', "any"),
        (r'^::1', "localhost IPv6"),
        (r'^fe80:', "link-local IPv6")
    ]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.connection_history: Dict[str, List[Dict]] = defaultdict(list)

    def get_active_connections(self) -> List[Dict[str, Any]]:
        """
        Obtém lista de conexões de rede ativas.

        Returns:
            Lista de conexões com detalhes
        """
        connections = []

        try:
            # Use ss command (modern replacement for netstat)
            cmd = ["ss", "-tunapH"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                parts = line.split()
                if len(parts) < 6:
                    continue

                conn = self._parse_ss_line(parts)
                if conn:
                    connections.append(conn)

        except subprocess.TimeoutExpired:
            pass
        except FileNotFoundError:
            # Fallback to netstat
            try:
                cmd = ["netstat", "-tuanp"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

                for line in result.stdout.strip().split("\n")[2:]:  # Skip header
                    conn = self._parse_netstat_line(line)
                    if conn:
                        connections.append(conn)
            except Exception:
                pass

        return connections

    def _parse_ss_line(self, parts: List[str]) -> Optional[Dict[str, Any]]:
        """Parse uma linha do comando ss."""
        try:
            protocol = parts[0]
            state = parts[1]
            local = parts[4]
            remote = parts[5]

            # Parse local address
            local_ip, local_port = self._parse_address(local)

            # Parse remote address
            remote_ip, remote_port = self._parse_address(remote)

            # Get process if available
            process = parts[6] if len(parts) > 6 else ""

            return {
                "protocol": protocol,
                "state": state,
                "local_ip": local_ip,
                "local_port": local_port,
                "remote_ip": remote_ip,
                "remote_port": remote_port,
                "process": process,
                "timestamp": datetime.now().isoformat()
            }
        except Exception:
            return None

    def _parse_netstat_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse uma linha do netstat."""
        try:
            parts = line.split()
            if len(parts) < 5:
                return None

            protocol = parts[0]
            local = parts[3]
            remote = parts[4]
            state = parts[5] if len(parts) > 5 else "UNKNOWN"

            local_ip, local_port = self._parse_address(local)
            remote_ip, remote_port = self._parse_address(remote)

            return {
                "protocol": protocol,
                "state": state,
                "local_ip": local_ip,
                "local_port": local_port,
                "remote_ip": remote_ip,
                "remote_port": remote_port,
                "process": parts[6] if len(parts) > 6 else "",
                "timestamp": datetime.now().isoformat()
            }
        except Exception:
            return None

    def _parse_address(self, addr: str) -> tuple:
        """Parse endereço no formato ip:porta."""
        if ']:' in addr:  # IPv6
            match = re.match(r'\[([^\]]+)\]:(\d+)', addr)
            if match:
                return match.group(1), int(match.group(2))
        elif ':' in addr:  # IPv4
            parts = addr.rsplit(':', 1)
            if len(parts) == 2:
                return parts[0], int(parts[1]) if parts[1] != '*' else 0

        return addr, 0

    def is_private_ip(self, ip: str) -> bool:
        """Verifica se é um IP privado."""
        for pattern, _ in self.PRIVATE_RANGES:
            if re.match(pattern, ip):
                return True
        return False

    def analyze_connections(self) -> Dict[str, Any]:
        """
        Analisa conexões e identifica padrões suspeitos.

        Returns:
            Análise com conexões suspeitas e recomendações
        """
        connections = self.get_active_connections()

        analysis = {
            "total_connections": len(connections),
            "established": 0,
            "listening": 0,
            "suspicious": [],
            "external_ips": set(),
            "recommendations": []
        }

        ip_connection_count = defaultdict(int)

        for conn in connections:
            state = conn.get("state", "").upper()

            if "ESTAB" in state:
                analysis["established"] += 1
            elif "LISTEN" in state:
                analysis["listening"] += 1

            remote_ip = conn.get("remote_ip", "")
            remote_port = conn.get("remote_port", 0)

            # Skip private IPs
            if self.is_private_ip(remote_ip) or not remote_ip:
                continue

            analysis["external_ips"].add(remote_ip)
            ip_connection_count[remote_ip] += 1

            # Check for suspicious ports
            if remote_port in self.SUSPICIOUS_PORTS:
                analysis["suspicious"].append({
                    "ip": remote_ip,
                    "port": remote_port,
                    "reason": f"Porta suspeita: {self.SUSPICIOUS_PORTS[remote_port]}",
                    "connection": conn
                })

            # Track for rate analysis
            self.connection_history[remote_ip].append(conn)

        # Check for IPs with many connections (possible scan/DoS)
        for ip, count in ip_connection_count.items():
            if count > 10:
                analysis["suspicious"].append({
                    "ip": ip,
                    "port": None,
                    "reason": f"Muitas conexões ({count}): possível scan ou DoS",
                    "connection_count": count
                })

        # Generate recommendations
        if analysis["suspicious"]:
            unique_suspicious = set(s["ip"] for s in analysis["suspicious"])
            for ip in unique_suspicious:
                analysis["recommendations"].append({
                    "action": "block",
                    "ip": ip,
                    "reason": "IP identificado como suspeito"
                })

        # Convert set to list for JSON serialization
        analysis["external_ips"] = list(analysis["external_ips"])

        return analysis

    def get_suspicious_ips(self) -> List[Dict[str, Any]]:
        """
        Obtém lista de IPs suspeitos com motivos.

        Returns:
            Lista de IPs suspeitos
        """
        analysis = self.analyze_connections()
        return analysis.get("suspicious", [])

    def get_connection_summary(self) -> str:
        """
        Retorna um resumo das conexões em formato texto.
        Útil para o agente.
        """
        analysis = self.analyze_connections()

        lines = [
            "=== Resumo de Conexões de Rede ===",
            f"Total de conexões: {analysis['total_connections']}",
            f"Estabelecidas: {analysis['established']}",
            f"À escuta: {analysis['listening']}",
            f"IPs externos: {len(analysis['external_ips'])}",
            ""
        ]

        if analysis["suspicious"]:
            lines.append("⚠️ Conexões Suspeitas:")
            for s in analysis["suspicious"][:10]:  # Limit output
                lines.append(f"  - {s['ip']}: {s['reason']}")
            lines.append("")

        if analysis["recommendations"]:
            lines.append("📋 Recomendações:")
            for r in analysis["recommendations"][:5]:
                lines.append(f"  - {r['action'].upper()} {r['ip']}: {r['reason']}")

        return "\n".join(lines)


# Wrapper function for agent tool interface
def scan_network() -> str:
    """
    Interface simplificada para scan de rede.
    Usada pelo agente.
    """
    monitor = NetworkMonitor()
    return monitor.get_connection_summary()


def get_suspicious() -> str:
    """
    Retorna lista de IPs suspeitos.
    """
    monitor = NetworkMonitor()
    suspicious = monitor.get_suspicious_ips()

    if not suspicious:
        return "Nenhum IP suspeito detectado nas conexões atuais."

    output = ["IPs Suspeitos Detectados:\n"]
    for s in suspicious:
        output.append(f"  🔴 {s['ip']}")
        output.append(f"     Motivo: {s['reason']}")
        if s.get("port"):
            output.append(f"     Porta: {s['port']}")
        output.append("")

    return "\n".join(output)
