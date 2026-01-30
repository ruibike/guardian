#!/usr/bin/env python3
"""
Guardian - Agente LLM Offline
Otimizado para sistemas com 8GB de RAM

Um agente AI local que:
- Raciocina autonomamente sobre problemas
- Pesquisa ficheiros no sistema Ubuntu
- Pesquisa informação na internet
- Gere o firewall (bloquear/desbloquear IPs)
- Grava todo o processo de raciocínio

Uso:
    python main.py          # Inicia interface gráfica GTK
    python main.py --cli    # Modo linha de comandos
    python main.py --help   # Ajuda
"""

import argparse
import os
import sys
import yaml
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


def load_config() -> dict:
    """Carrega a configuração do ficheiro config.yaml."""
    config_path = Path(__file__).parent / "config.yaml"
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print("[AVISO] config.yaml não encontrado. Usando configuração padrão.")
        return {
            "llm": {
                "model_path": "~/.local/share/guardian/models/mistral-7b-instruct-v0.2.Q4_K_M.gguf",
                "n_ctx": 2048,
                "n_batch": 256,
                "n_threads": 4,
                "n_gpu_layers": 0,
                "temperature": 0.7,
                "max_tokens": 512
            },
            "reasoning": {
                "enabled": True,
                "save_to_file": True,
                "log_dir": "data/reasoning",
                "max_steps": 10
            },
            "firewall": {
                "enabled": True,
                "blocked_ips_file": "data/blocked_ips/blocked.txt"
            },
            "tools": {
                "file_search": {
                    "enabled": True,
                    "search_paths": ["~"]
                },
                "web_search": {
                    "enabled": True,
                    "max_results": 5
                }
            }
        }


def run_cli(config: dict):
    """Executa o Guardian em modo CLI."""
    from agent.llm_agent import GuardianAgent
    from agent.instructions import get_help_message
    from tools.firewall import block_ip, unblock_ip, list_blocked_ips
    from tools.file_search import file_search
    from tools.web_search import web_search
    from tools.network_monitor import scan_network, get_suspicious

    # Banner
    print("\033[94m")
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║                                                           ║")
    print("║   ██████╗ ██╗   ██╗ █████╗ ██████╗ ██████╗ ██╗ █████╗ ███╗   ██╗  ║")
    print("║  ██╔════╝ ██║   ██║██╔══██╗██╔══██╗██╔══██╗██║██╔══██╗████╗  ██║  ║")
    print("║  ██║  ███╗██║   ██║███████║██████╔╝██║  ██║██║███████║██╔██╗ ██║  ║")
    print("║  ██║   ██║██║   ██║██╔══██║██╔══██╗██║  ██║██║██╔══██║██║╚██╗██║  ║")
    print("║  ╚██████╔╝╚██████╔╝██║  ██║██║  ██║██████╔╝██║██║  ██║██║ ╚████║  ║")
    print("║   ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝  ║")
    print("║                                                           ║")
    print("║          Agente LLM Offline - Otimizado 8GB RAM           ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print("\033[0m")
    print()
    print("Comandos rápidos: /help para ver todos | /quit para sair")
    print("-" * 60)
    print()

    # Initialize agent with tools
    tools = {
        "file_search": file_search,
        "web_search": web_search,
        "block_ip": block_ip,
        "unblock_ip": unblock_ip,
        "list_blocked_ips": list_blocked_ips,
        "scan_network": scan_network,
        "get_suspicious": get_suspicious,
    }

    agent = GuardianAgent(config, tools)
    agent.initialize()

    while True:
        try:
            user_input = input("\n[Tu]: ").strip()

            if not user_input:
                continue

            # Handle special commands
            if user_input.lower() in ['/quit', '/exit', 'quit', 'exit']:
                print("\nAdeus! O Guardian está a encerrar.")
                break

            elif user_input.lower() == '/clear':
                agent.clear_history()
                print("[Sistema]: Histórico limpo.")
                continue

            elif user_input.lower() == '/blocked':
                print(list_blocked_ips())
                continue

            elif user_input.lower().startswith('/block '):
                ip = user_input[7:].strip()
                print(block_ip(ip))
                continue

            elif user_input.lower().startswith('/unblock '):
                ip = user_input[9:].strip()
                print(unblock_ip(ip))
                continue

            elif user_input.lower().startswith('/search '):
                query = user_input[8:].strip()
                print(file_search(query))
                continue

            elif user_input.lower().startswith('/web '):
                query = user_input[5:].strip()
                print(web_search(query))
                continue

            elif user_input.lower() in ['/scan', '/network', '/rede']:
                print("\n[Guardian]: A analisar conexões de rede...\n")
                print(scan_network())
                continue

            elif user_input.lower() in ['/suspicious', '/suspeitos']:
                print("\n[Guardian]: A verificar IPs suspeitos...\n")
                print(get_suspicious())
                continue

            elif user_input.lower() in ['/about', '/sobre']:
                print(get_help_message("about"))
                continue

            elif user_input.lower() == '/help':
                print("""
╔═══════════════════════════════════════════════════════════╗
║                   COMANDOS GUARDIAN                       ║
╠═══════════════════════════════════════════════════════════╣
║                                                           ║
║  NAVEGAÇÃO                                                ║
║    /quit, /exit     Sair do Guardian                      ║
║    /clear           Limpar histórico de conversação       ║
║    /help            Mostrar esta ajuda                    ║
║    /about           Sobre o Guardian                      ║
║                                                           ║
║  FIREWALL                                                 ║
║    /blocked         Listar IPs bloqueados                 ║
║    /block <ip>      Bloquear um IP                        ║
║    /unblock <ip>    Desbloquear um IP                     ║
║                                                           ║
║  PESQUISA                                                 ║
║    /search <query>  Pesquisar ficheiros por nome          ║
║    /web <query>     Pesquisar na internet (DuckDuckGo)    ║
║                                                           ║
║  SEGURANÇA                                                ║
║    /scan            Analisar conexões de rede             ║
║    /suspicious      Mostrar IPs suspeitos                 ║
║                                                           ║
╠═══════════════════════════════════════════════════════════╣
║                                                           ║
║  Podes também conversar naturalmente com o agente:        ║
║  > "bloqueia o IP 192.168.1.100"                          ║
║  > "pesquisa ficheiros de configuração"                   ║
║  > "verifica a segurança do sistema"                      ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
                """)
                continue

            # Normal conversation with agent
            print("\n[Guardian]: ", end="", flush=True)
            response = agent.think(user_input)
            print(response)

        except KeyboardInterrupt:
            print("\n\nInterrompido. A sair...")
            break
        except EOFError:
            print("\n\nFim de entrada. A sair...")
            break


def run_gui():
    """Executa o Guardian com interface grafica (CustomTkinter)."""
    try:
        from ui.main_window import run_app
        return run_app()
    except ImportError as e:
        print(f"[ERRO] Nao foi possivel carregar a interface grafica: {e}")
        print("\nInstale as dependencias:")
        print("  pip install customtkinter")
        print("\nOu execute em modo CLI:")
        print("  python main.py --cli")
        sys.exit(1)


def check_system_requirements():
    """Verifica requisitos do sistema."""
    import psutil

    print("=== Verificação do Sistema ===\n")

    # RAM
    ram = psutil.virtual_memory()
    ram_gb = ram.total / (1024 ** 3)
    print(f"RAM Total: {ram_gb:.1f} GB")
    print(f"RAM Disponível: {ram.available / (1024 ** 3):.1f} GB")

    if ram_gb < 8:
        print("[AVISO] Sistema com menos de 8GB de RAM.")
        print("        Recomenda-se usar um modelo mais pequeno (phi-2, tinyllama)")

    # CPU
    cpu_count = psutil.cpu_count()
    print(f"CPUs: {cpu_count}")

    # Check for model
    model_path = os.path.expanduser(
        "~/.local/share/guardian/models/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
    )
    if os.path.exists(model_path):
        size_gb = os.path.getsize(model_path) / (1024 ** 3)
        print(f"Modelo encontrado: {model_path} ({size_gb:.1f} GB)")
    else:
        print(f"[INFO] Modelo não encontrado em: {model_path}")
        print("       O Guardian funcionará em modo simulado.")
        print()
        print("Para instalar um modelo:")
        print("  mkdir -p ~/.local/share/guardian/models")
        print("  cd ~/.local/share/guardian/models")
        print("  wget https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf")

    print()


def main():
    """Ponto de entrada principal."""
    parser = argparse.ArgumentParser(
        description="Guardian - Agente LLM Offline para Ubuntu",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python main.py              # Inicia com interface gráfica
  python main.py --cli        # Modo linha de comandos
  python main.py --check      # Verifica requisitos do sistema

O Guardian é otimizado para sistemas com 8GB de RAM.
        """
    )

    parser.add_argument(
        '--cli',
        action='store_true',
        help='Executar em modo linha de comandos'
    )

    parser.add_argument(
        '--check',
        action='store_true',
        help='Verificar requisitos do sistema'
    )

    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Caminho para ficheiro de configuração'
    )

    args = parser.parse_args()

    # Load configuration
    config = load_config()

    if args.check:
        check_system_requirements()
        return

    if args.cli:
        run_cli(config)
    else:
        run_gui()


if __name__ == "__main__":
    main()
