"""
File Search Tool - Pesquisa de ficheiros no sistema Ubuntu
"""

import os
import fnmatch
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


class FileSearchTool:
    """
    Ferramenta para pesquisa de ficheiros no sistema.
    Usa métodos nativos Python e comandos do sistema quando necessário.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.search_paths = [
            os.path.expanduser(p)
            for p in config.get("search_paths", ["~"])
        ]
        self.excluded_dirs = set(config.get("excluded_dirs", [
            ".git", "node_modules", "__pycache__", ".cache", ".local/share/Trash"
        ]))
        self.max_results = config.get("max_results", 50)

    def search_by_name(self, query: str, path: Optional[str] = None,
                       recursive: bool = True) -> List[Dict[str, Any]]:
        """
        Pesquisa ficheiros por nome.

        Args:
            query: Padrão de pesquisa (suporta wildcards * e ?)
            path: Caminho base para pesquisa (opcional)
            recursive: Se deve pesquisar em subdiretórios

        Returns:
            Lista de ficheiros encontrados com metadados
        """
        search_path = os.path.expanduser(path) if path else self.search_paths[0]
        results = []

        # Add wildcards if not present
        if '*' not in query and '?' not in query:
            query = f"*{query}*"

        try:
            if recursive:
                for root, dirs, files in os.walk(search_path):
                    # Filter excluded directories
                    dirs[:] = [d for d in dirs if d not in self.excluded_dirs]

                    for filename in files:
                        if fnmatch.fnmatch(filename.lower(), query.lower()):
                            filepath = os.path.join(root, filename)
                            results.append(self._get_file_info(filepath))

                            if len(results) >= self.max_results:
                                return results
            else:
                for item in os.listdir(search_path):
                    if fnmatch.fnmatch(item.lower(), query.lower()):
                        filepath = os.path.join(search_path, item)
                        results.append(self._get_file_info(filepath))

                        if len(results) >= self.max_results:
                            return results

        except PermissionError:
            pass
        except Exception as e:
            results.append({"error": str(e)})

        return results

    def search_by_content(self, query: str, path: Optional[str] = None,
                          file_pattern: str = "*") -> List[Dict[str, Any]]:
        """
        Pesquisa ficheiros pelo conteúdo usando grep.

        Args:
            query: Texto a pesquisar
            path: Caminho base para pesquisa
            file_pattern: Padrão de ficheiros a pesquisar (ex: "*.py")

        Returns:
            Lista de ficheiros com linhas correspondentes
        """
        search_path = os.path.expanduser(path) if path else self.search_paths[0]
        results = []

        try:
            # Use grep for content search (more efficient)
            cmd = [
                "grep", "-r", "-l", "-i",
                "--include", file_pattern,
                query, search_path
            ]

            # Add exclusions
            for excl in self.excluded_dirs:
                cmd.extend(["--exclude-dir", excl])

            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            for line in process.stdout.strip().split("\n"):
                if line:
                    filepath = line.strip()
                    if os.path.exists(filepath):
                        file_info = self._get_file_info(filepath)
                        file_info["matched_content"] = self._get_matching_lines(
                            filepath, query
                        )
                        results.append(file_info)

                        if len(results) >= self.max_results:
                            break

        except subprocess.TimeoutExpired:
            results.append({"error": "Pesquisa excedeu tempo limite"})
        except Exception as e:
            results.append({"error": str(e)})

        return results

    def _get_matching_lines(self, filepath: str, query: str,
                            context_lines: int = 1) -> List[Dict[str, Any]]:
        """Obtém as linhas que correspondem à pesquisa."""
        matches = []
        query_lower = query.lower()

        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            for i, line in enumerate(lines):
                if query_lower in line.lower():
                    matches.append({
                        "line_number": i + 1,
                        "content": line.strip()[:200]  # Limit line length
                    })

                    if len(matches) >= 5:  # Limit matches per file
                        break

        except Exception:
            pass

        return matches

    def _get_file_info(self, filepath: str) -> Dict[str, Any]:
        """Obtém informações detalhadas de um ficheiro."""
        try:
            stat = os.stat(filepath)
            return {
                "path": filepath,
                "name": os.path.basename(filepath),
                "size": stat.st_size,
                "size_human": self._human_size(stat.st_size),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "is_dir": os.path.isdir(filepath),
                "permissions": oct(stat.st_mode)[-3:]
            }
        except Exception as e:
            return {
                "path": filepath,
                "error": str(e)
            }

    def _human_size(self, size: int) -> str:
        """Converte tamanho em bytes para formato legível."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    def find_recent(self, path: Optional[str] = None,
                    days: int = 7, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Encontra ficheiros modificados recentemente.

        Args:
            path: Caminho base
            days: Número de dias
            limit: Máximo de resultados

        Returns:
            Lista de ficheiros recentes
        """
        search_path = os.path.expanduser(path) if path else self.search_paths[0]
        results = []

        try:
            cmd = [
                "find", search_path,
                "-type", "f",
                "-mtime", f"-{days}",
                "-printf", "%T@ %p\n"
            ]

            # Add exclusions
            for excl in self.excluded_dirs:
                cmd.insert(2, "-not")
                cmd.insert(3, "-path")
                cmd.insert(4, f"*/{excl}/*")

            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            # Parse and sort by modification time
            files = []
            for line in process.stdout.strip().split("\n"):
                if line:
                    parts = line.split(" ", 1)
                    if len(parts) == 2:
                        try:
                            mtime = float(parts[0])
                            filepath = parts[1]
                            files.append((mtime, filepath))
                        except ValueError:
                            continue

            # Sort by modification time (newest first)
            files.sort(reverse=True)

            for _, filepath in files[:limit]:
                if os.path.exists(filepath):
                    results.append(self._get_file_info(filepath))

        except subprocess.TimeoutExpired:
            results.append({"error": "Pesquisa excedeu tempo limite"})
        except Exception as e:
            results.append({"error": str(e)})

        return results

    def read_file(self, filepath: str, max_lines: int = 100) -> Dict[str, Any]:
        """
        Lê o conteúdo de um ficheiro.

        Args:
            filepath: Caminho do ficheiro
            max_lines: Máximo de linhas a ler

        Returns:
            Conteúdo do ficheiro e metadados
        """
        filepath = os.path.expanduser(filepath)

        if not os.path.exists(filepath):
            return {"error": f"Ficheiro não encontrado: {filepath}"}

        if os.path.isdir(filepath):
            return {"error": f"É um diretório: {filepath}"}

        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            total_lines = len(lines)
            content = "".join(lines[:max_lines])

            return {
                "path": filepath,
                "content": content,
                "total_lines": total_lines,
                "lines_shown": min(max_lines, total_lines),
                "truncated": total_lines > max_lines
            }

        except Exception as e:
            return {"error": str(e)}


# Wrapper function for agent tool interface
def file_search(query: str, path: str = "~", content: bool = False) -> str:
    """
    Interface simplificada para pesquisa de ficheiros.
    Usada pelo agente.
    """
    tool = FileSearchTool({})

    if content:
        results = tool.search_by_content(query, path)
    else:
        results = tool.search_by_name(query, path)

    if not results:
        return "Nenhum ficheiro encontrado."

    output = [f"Encontrados {len(results)} ficheiro(s):\n"]
    for r in results[:10]:  # Limit output
        if "error" in r:
            output.append(f"  ⚠️ Erro: {r['error']}")
        else:
            output.append(f"  📄 {r['path']}")
            output.append(f"     Tamanho: {r.get('size_human', 'N/A')}")
            if "matched_content" in r:
                for match in r["matched_content"][:2]:
                    output.append(f"     L{match['line_number']}: {match['content'][:60]}...")

    return "\n".join(output)
