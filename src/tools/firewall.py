"""
Firewall Manager - Gestão de IPs Bloqueados
Integra com iptables/nftables no Ubuntu
"""

import os
import re
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


class FirewallManager:
    """
    Gestor de firewall para bloquear/desbloquear IPs.
    Mantém uma lista local e pode integrar com iptables.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.blocked_ips_file = Path(
            os.path.expanduser(config.get("blocked_ips_file", "data/blocked_ips/blocked.txt"))
        )
        self.blocked_ips_file.parent.mkdir(parents=True, exist_ok=True)
        self.use_iptables = config.get("use_iptables", False)

        # Initialize blocked IPs list
        self.blocked_ips: Dict[str, Dict[str, Any]] = {}
        self._load_blocked_ips()

    def _load_blocked_ips(self):
        """Carrega a lista de IPs bloqueados do ficheiro."""
        if self.blocked_ips_file.exists():
            try:
                with open(self.blocked_ips_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.blocked_ips = data if isinstance(data, dict) else {}
            except (json.JSONDecodeError, IOError):
                self.blocked_ips = {}

    def _save_blocked_ips(self):
        """Guarda a lista de IPs bloqueados no ficheiro."""
        with open(self.blocked_ips_file, 'w', encoding='utf-8') as f:
            json.dump(self.blocked_ips, f, indent=2, ensure_ascii=False)

    def _is_valid_ip(self, ip: str) -> bool:
        """Verifica se é um IP válido (IPv4 ou IPv6)."""
        # IPv4 pattern
        ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if re.match(ipv4_pattern, ip):
            parts = ip.split('.')
            return all(0 <= int(p) <= 255 for p in parts)

        # IPv6 pattern (simplified)
        ipv6_pattern = r'^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}$'
        if re.match(ipv6_pattern, ip):
            return True

        # CIDR notation
        cidr_pattern = r'^(\d{1,3}\.){3}\d{1,3}/\d{1,2}$'
        if re.match(cidr_pattern, ip):
            return True

        return False

    def block_ip(self, ip: str, reason: str = "Manual block",
                 duration: Optional[int] = None) -> Dict[str, Any]:
        """
        Bloqueia um IP.

        Args:
            ip: Endereço IP a bloquear
            reason: Motivo do bloqueio
            duration: Duração em horas (None = permanente)

        Returns:
            Resultado da operação
        """
        if not self._is_valid_ip(ip):
            return {"success": False, "error": f"IP inválido: {ip}"}

        if ip in self.blocked_ips:
            return {"success": False, "error": f"IP já está bloqueado: {ip}"}

        # Add to local list
        entry = {
            "ip": ip,
            "reason": reason,
            "blocked_at": datetime.now().isoformat(),
            "duration_hours": duration,
            "expires_at": None
        }

        if duration:
            from datetime import timedelta
            expires = datetime.now() + timedelta(hours=duration)
            entry["expires_at"] = expires.isoformat()

        self.blocked_ips[ip] = entry
        self._save_blocked_ips()

        # Apply to iptables if enabled and running as root
        iptables_result = None
        if self.use_iptables and os.geteuid() == 0:
            iptables_result = self._add_iptables_rule(ip)

        return {
            "success": True,
            "ip": ip,
            "reason": reason,
            "iptables_applied": iptables_result
        }

    def unblock_ip(self, ip: str) -> Dict[str, Any]:
        """
        Desbloqueia um IP.

        Args:
            ip: Endereço IP a desbloquear

        Returns:
            Resultado da operação
        """
        if ip not in self.blocked_ips:
            return {"success": False, "error": f"IP não está bloqueado: {ip}"}

        # Remove from local list
        del self.blocked_ips[ip]
        self._save_blocked_ips()

        # Remove from iptables if enabled
        iptables_result = None
        if self.use_iptables and os.geteuid() == 0:
            iptables_result = self._remove_iptables_rule(ip)

        return {
            "success": True,
            "ip": ip,
            "iptables_removed": iptables_result
        }

    def list_blocked(self) -> List[Dict[str, Any]]:
        """
        Lista todos os IPs bloqueados.

        Returns:
            Lista de IPs bloqueados com metadados
        """
        result = []
        for ip, data in self.blocked_ips.items():
            entry = {
                "ip": ip,
                "reason": data.get("reason", ""),
                "blocked_at": data.get("blocked_at", ""),
                "expires_at": data.get("expires_at"),
                "is_permanent": data.get("duration_hours") is None
            }
            result.append(entry)

        # Sort by blocked_at (newest first)
        result.sort(key=lambda x: x.get("blocked_at", ""), reverse=True)
        return result

    def is_blocked(self, ip: str) -> bool:
        """Verifica se um IP está bloqueado."""
        if ip not in self.blocked_ips:
            return False

        # Check if expired
        entry = self.blocked_ips[ip]
        if entry.get("expires_at"):
            expires = datetime.fromisoformat(entry["expires_at"])
            if datetime.now() > expires:
                # Auto-unblock expired entries
                self.unblock_ip(ip)
                return False

        return True

    def get_statistics(self) -> Dict[str, Any]:
        """
        Obtém estatísticas dos IPs bloqueados.

        Returns:
            Estatísticas de bloqueio
        """
        total = len(self.blocked_ips)
        permanent = sum(1 for d in self.blocked_ips.values() if d.get("duration_hours") is None)
        temporary = total - permanent

        return {
            "total_blocked": total,
            "permanent": permanent,
            "temporary": temporary,
            "file_path": str(self.blocked_ips_file)
        }

    def _add_iptables_rule(self, ip: str) -> Dict[str, Any]:
        """Adiciona regra ao iptables."""
        try:
            cmd = ["iptables", "-A", "INPUT", "-s", ip, "-j", "DROP"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

            if result.returncode == 0:
                return {"success": True, "command": " ".join(cmd)}
            else:
                return {"success": False, "error": result.stderr}

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _remove_iptables_rule(self, ip: str) -> Dict[str, Any]:
        """Remove regra do iptables."""
        try:
            cmd = ["iptables", "-D", "INPUT", "-s", ip, "-j", "DROP"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

            if result.returncode == 0:
                return {"success": True, "command": " ".join(cmd)}
            else:
                return {"success": False, "error": result.stderr}

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def export_to_hosts_deny(self, filepath: str = "/etc/hosts.deny") -> Dict[str, Any]:
        """
        Exporta IPs bloqueados para /etc/hosts.deny.
        Requer permissões de root.
        """
        try:
            lines = ["# Generated by Guardian\n"]
            for ip in self.blocked_ips:
                lines.append(f"ALL: {ip}\n")

            with open(filepath, 'a', encoding='utf-8') as f:
                f.writelines(lines)

            return {"success": True, "file": filepath, "ips_exported": len(self.blocked_ips)}

        except PermissionError:
            return {"success": False, "error": "Permissão negada. Execute como root."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def import_from_file(self, filepath: str) -> Dict[str, Any]:
        """
        Importa IPs de um ficheiro (um IP por linha).

        Args:
            filepath: Caminho do ficheiro

        Returns:
            Resultado da importação
        """
        imported = 0
        errors = []

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    ip = line.strip()
                    if ip and not ip.startswith('#'):
                        result = self.block_ip(ip, reason=f"Importado de {filepath}")
                        if result["success"]:
                            imported += 1
                        else:
                            errors.append(result.get("error", ""))

            return {
                "success": True,
                "imported": imported,
                "errors": errors if errors else None
            }

        except Exception as e:
            return {"success": False, "error": str(e)}


# Wrapper functions for agent tool interface
def block_ip(ip: str, reason: str = "Bloqueio manual") -> str:
    """Interface simplificada para bloquear IP."""
    manager = FirewallManager({"blocked_ips_file": "data/blocked_ips/blocked.txt"})
    result = manager.block_ip(ip, reason)

    if result["success"]:
        return f"✅ IP {ip} bloqueado com sucesso.\nMotivo: {reason}"
    else:
        return f"❌ Erro ao bloquear {ip}: {result.get('error', 'Erro desconhecido')}"


def unblock_ip(ip: str) -> str:
    """Interface simplificada para desbloquear IP."""
    manager = FirewallManager({"blocked_ips_file": "data/blocked_ips/blocked.txt"})
    result = manager.unblock_ip(ip)

    if result["success"]:
        return f"✅ IP {ip} desbloqueado com sucesso."
    else:
        return f"❌ Erro ao desbloquear {ip}: {result.get('error', 'Erro desconhecido')}"


def list_blocked_ips() -> str:
    """Interface simplificada para listar IPs bloqueados."""
    manager = FirewallManager({"blocked_ips_file": "data/blocked_ips/blocked.txt"})
    blocked = manager.list_blocked()

    if not blocked:
        return "Nenhum IP bloqueado."

    output = [f"IPs Bloqueados ({len(blocked)}):\n"]
    output.append("-" * 60)

    for entry in blocked:
        status = "🔒 Permanente" if entry["is_permanent"] else f"⏰ Expira: {entry['expires_at']}"
        output.append(f"\n  IP: {entry['ip']}")
        output.append(f"  Motivo: {entry['reason']}")
        output.append(f"  Bloqueado em: {entry['blocked_at']}")
        output.append(f"  Status: {status}")

    return "\n".join(output)
