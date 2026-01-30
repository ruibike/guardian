"""
Guardian UI - Interface CustomTkinter Principal
Aplicacao com separadores (tabs) para diferentes funcionalidades
Versao portavel - funciona em qualquer Linux com pip install
"""

import customtkinter as ctk
import threading
import os
import sys
from tkinter import ttk
import tkinter as tk

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.llm_agent import GuardianAgent
from agent.reasoning import ReasoningEngine
from tools.firewall import FirewallManager
from tools.file_search import FileSearchTool
from tools.web_search import WebSearchTool

# Configure CustomTkinter
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class GuardianApp:
    """Aplicacao principal Guardian."""

    def __init__(self):
        self.config = self._load_config()
        self.agent = None
        self.firewall = None
        self.reasoning_engine = None
        self.window = None

    def _load_config(self):
        """Carrega configuracao."""
        import yaml
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'config.yaml'
        )
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception:
            return {
                "llm": {"n_ctx": 2048, "n_threads": 4},
                "reasoning": {"save_to_file": True, "log_dir": "data/reasoning"},
                "firewall": {"blocked_ips_file": "data/blocked_ips/blocked.txt"}
            }

    def initialize(self):
        """Inicializa componentes."""
        self.firewall = FirewallManager(self.config.get("firewall", {}))
        self.reasoning_engine = ReasoningEngine(self.config.get("reasoning", {}))

        tools = {
            "file_search": self._tool_file_search,
            "web_search": self._tool_web_search,
            "block_ip": self._tool_block_ip,
            "unblock_ip": self._tool_unblock_ip,
            "list_blocked_ips": self._tool_list_blocked_ips,
        }

        self.agent = GuardianAgent(self.config, tools)
        self.agent.initialize()

    def _tool_file_search(self, query: str, path: str = "~") -> str:
        """Tool wrapper for file search."""
        tool = FileSearchTool(self.config.get("tools", {}).get("file_search", {}))
        results = tool.search_by_name(query, path)
        if not results:
            return "Nenhum ficheiro encontrado."
        output = [f"Encontrados {len(results)} ficheiro(s):"]
        for r in results[:10]:
            output.append(f"  - {r.get('path', 'N/A')}")
        return "\n".join(output)

    def _tool_web_search(self, query: str) -> str:
        """Tool wrapper for web search."""
        tool = WebSearchTool(self.config.get("tools", {}).get("web_search", {}))
        results = tool.search(query)
        if not results:
            return "Nenhum resultado encontrado."
        output = [f"Resultados para '{query}':"]
        for r in results[:5]:
            output.append(f"  - {r.get('title', 'N/A')}: {r.get('url', '')}")
        return "\n".join(output)

    def _tool_block_ip(self, ip: str, reason: str = "Manual") -> str:
        """Tool wrapper for blocking IP."""
        result = self.firewall.block_ip(ip, reason)
        if result["success"]:
            if self.window:
                self.window.after(0, self.window.refresh_blocked_ips)
            return f"IP {ip} bloqueado com sucesso."
        return f"Erro: {result.get('error', 'Desconhecido')}"

    def _tool_unblock_ip(self, ip: str) -> str:
        """Tool wrapper for unblocking IP."""
        result = self.firewall.unblock_ip(ip)
        if result["success"]:
            if self.window:
                self.window.after(0, self.window.refresh_blocked_ips)
            return f"IP {ip} desbloqueado."
        return f"Erro: {result.get('error', 'Desconhecido')}"

    def _tool_list_blocked_ips(self) -> str:
        """Tool wrapper for listing blocked IPs."""
        blocked = self.firewall.list_blocked()
        if not blocked:
            return "Nenhum IP bloqueado."
        output = [f"IPs Bloqueados ({len(blocked)}):"]
        for entry in blocked:
            output.append(f"  - {entry['ip']}: {entry['reason']}")
        return "\n".join(output)

    def run(self):
        """Executa a aplicacao."""
        self.initialize()
        self.window = MainWindow(self)
        self.window.mainloop()


class MainWindow(ctk.CTk):
    """Janela principal com separadores."""

    def __init__(self, app: GuardianApp):
        super().__init__()
        self.app_ref = app

        self.title("Guardian - Agente LLM Offline")
        self.geometry("1200x800")
        self.minsize(800, 600)

        # Main layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        self._create_header()

        # Tabview (tabs)
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="nsew")

        # Create tabs
        self.tab_chat = self.tabview.add("Chat")
        self.tab_blocked = self.tabview.add("IPs Bloqueados")
        self.tab_reasoning = self.tabview.add("Raciocinio")
        self.tab_tools = self.tabview.add("Ferramentas")

        self._create_chat_tab()
        self._create_blocked_ips_tab()
        self._create_reasoning_tab()
        self._create_tools_tab()

        # Status bar
        self.status_var = ctk.StringVar(value="Pronto")
        self.status_bar = ctk.CTkLabel(
            self,
            textvariable=self.status_var,
            anchor="w",
            height=25
        )
        self.status_bar.grid(row=2, column=0, padx=10, pady=(0, 5), sticky="ew")

        # Initial data load
        self.after(100, self.refresh_blocked_ips)

    def _create_header(self):
        """Cria o cabecalho."""
        header_frame = ctk.CTkFrame(self, height=50)
        header_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        title_label = ctk.CTkLabel(
            header_frame,
            text="Guardian",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="Agente LLM Offline - Linux Safe Mode",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        subtitle_label.grid(row=0, column=1, padx=20, pady=10)

        # Theme toggle
        self.theme_switch = ctk.CTkSwitch(
            header_frame,
            text="Tema Escuro",
            command=self._toggle_theme,
            onvalue="Dark",
            offvalue="Light"
        )
        self.theme_switch.grid(row=0, column=2, padx=20, pady=10, sticky="e")
        self.theme_switch.select()

    def _toggle_theme(self):
        """Alterna entre tema claro e escuro."""
        mode = self.theme_switch.get()
        ctk.set_appearance_mode(mode)

    def _create_chat_tab(self):
        """Cria a tab de chat com o agente."""
        self.tab_chat.grid_columnconfigure(0, weight=1)
        self.tab_chat.grid_rowconfigure(0, weight=1)

        # Chat frame
        chat_frame = ctk.CTkFrame(self.tab_chat)
        chat_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        chat_frame.grid_columnconfigure(0, weight=1)
        chat_frame.grid_rowconfigure(0, weight=1)

        # Chat history (scrollable textbox)
        self.chat_textbox = ctk.CTkTextbox(
            chat_frame,
            wrap="word",
            font=ctk.CTkFont(size=13)
        )
        self.chat_textbox.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.chat_textbox.configure(state="disabled")

        # Welcome message
        self._append_to_chat(
            "=== Guardian - Agente LLM Offline ===\n\n"
            "Ola! Sou o Guardian, o teu assistente AI local.\n"
            "Posso ajudar-te com:\n"
            "  - Pesquisar ficheiros no sistema\n"
            "  - Pesquisar na internet\n"
            "  - Gerir o firewall (bloquear/desbloquear IPs)\n"
            "  - Raciocinar sobre problemas complexos\n\n"
            "Escreve a tua mensagem abaixo...\n\n"
        )

        # Input area
        input_frame = ctk.CTkFrame(self.tab_chat)
        input_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)

        self.chat_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Escreve a tua mensagem...",
            height=40
        )
        self.chat_entry.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="ew")
        self.chat_entry.bind("<Return>", self._on_send_message)

        send_button = ctk.CTkButton(
            input_frame,
            text="Enviar",
            width=100,
            command=self._on_send_message
        )
        send_button.grid(row=0, column=1, padx=5, pady=10)

        clear_button = ctk.CTkButton(
            input_frame,
            text="Limpar",
            width=80,
            fg_color="gray",
            command=self._on_clear_chat
        )
        clear_button.grid(row=0, column=2, padx=(5, 10), pady=10)

    def _append_to_chat(self, text):
        """Adiciona texto ao chat."""
        self.chat_textbox.configure(state="normal")
        self.chat_textbox.insert("end", text)
        self.chat_textbox.configure(state="disabled")
        self.chat_textbox.see("end")

    def _create_blocked_ips_tab(self):
        """Cria a tab de IPs bloqueados."""
        self.tab_blocked.grid_columnconfigure(0, weight=1)
        self.tab_blocked.grid_rowconfigure(1, weight=1)

        # Header
        header_frame = ctk.CTkFrame(self.tab_blocked)
        header_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)

        title = ctk.CTkLabel(
            header_frame,
            text="IPs Bloqueados",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.blocked_stats_var = ctk.StringVar(value="Total: 0 | Permanentes: 0 | Temporarios: 0")
        stats_label = ctk.CTkLabel(
            header_frame,
            textvariable=self.blocked_stats_var
        )
        stats_label.grid(row=0, column=1, padx=10, pady=10)

        refresh_btn = ctk.CTkButton(
            header_frame,
            text="Atualizar",
            width=100,
            command=self.refresh_blocked_ips
        )
        refresh_btn.grid(row=0, column=2, padx=10, pady=10, sticky="e")

        # List frame with Treeview (using ttk for table)
        list_frame = ctk.CTkFrame(self.tab_blocked)
        list_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)

        # Style for treeview
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background="#2b2b2b",
            foreground="white",
            fieldbackground="#2b2b2b",
            rowheight=30
        )
        style.configure(
            "Treeview.Heading",
            background="#1f538d",
            foreground="white",
            font=('Helvetica', 11, 'bold')
        )
        style.map("Treeview", background=[("selected", "#1f538d")])

        # Treeview
        columns = ("IP", "Motivo", "Bloqueado em", "Status")
        self.blocked_tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )

        for col in columns:
            self.blocked_tree.heading(col, text=col)
            self.blocked_tree.column(col, width=150 if col == "IP" else 200)

        self.blocked_tree.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Scrollbar
        scrollbar = ctk.CTkScrollbar(list_frame, command=self.blocked_tree.yview)
        scrollbar.grid(row=0, column=1, pady=10, sticky="ns")
        self.blocked_tree.configure(yscrollcommand=scrollbar.set)

        # Actions frame
        actions_frame = ctk.CTkFrame(self.tab_blocked)
        actions_frame.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")
        actions_frame.grid_columnconfigure(0, weight=1)

        self.add_ip_entry = ctk.CTkEntry(
            actions_frame,
            placeholder_text="IP a bloquear (ex: 192.168.1.100)",
            width=250
        )
        self.add_ip_entry.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.add_reason_entry = ctk.CTkEntry(
            actions_frame,
            placeholder_text="Motivo",
            width=200
        )
        self.add_reason_entry.grid(row=0, column=1, padx=5, pady=10)

        block_btn = ctk.CTkButton(
            actions_frame,
            text="Bloquear IP",
            fg_color="#c42b1c",
            hover_color="#a02010",
            command=self._on_block_ip
        )
        block_btn.grid(row=0, column=2, padx=5, pady=10)

        unblock_btn = ctk.CTkButton(
            actions_frame,
            text="Desbloquear Selecionado",
            fg_color="gray",
            command=self._on_unblock_ip
        )
        unblock_btn.grid(row=0, column=3, padx=10, pady=10)

    def _create_reasoning_tab(self):
        """Cria a tab de historico de raciocinio."""
        self.tab_reasoning.grid_columnconfigure(0, weight=1)
        self.tab_reasoning.grid_rowconfigure(1, weight=1)

        # Header
        header_frame = ctk.CTkFrame(self.tab_reasoning)
        header_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        title = ctk.CTkLabel(
            header_frame,
            text="Historico de Raciocinio",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        desc = ctk.CTkLabel(
            header_frame,
            text="O Guardian grava todo o seu processo de raciocinio para analise posterior.",
            text_color="gray"
        )
        desc.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="w")

        # Reasoning textbox
        self.reasoning_textbox = ctk.CTkTextbox(
            self.tab_reasoning,
            wrap="word",
            font=ctk.CTkFont(size=12)
        )
        self.reasoning_textbox.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.reasoning_textbox.insert(
            "1.0",
            "Nenhuma sessao de raciocinio ainda.\n\n"
            "O raciocinio sera gravado automaticamente durante as interacoes."
        )
        self.reasoning_textbox.configure(state="disabled")

        # Buttons
        btn_frame = ctk.CTkFrame(self.tab_reasoning)
        btn_frame.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")

        refresh_btn = ctk.CTkButton(
            btn_frame,
            text="Atualizar",
            width=100,
            command=self._on_refresh_reasoning
        )
        refresh_btn.grid(row=0, column=0, padx=10, pady=10)

        clear_btn = ctk.CTkButton(
            btn_frame,
            text="Limpar Historico",
            width=120,
            fg_color="gray",
            command=self._on_clear_reasoning
        )
        clear_btn.grid(row=0, column=1, padx=5, pady=10)

    def _create_tools_tab(self):
        """Cria a tab de ferramentas."""
        self.tab_tools.grid_columnconfigure(0, weight=1)
        self.tab_tools.grid_rowconfigure(2, weight=1)

        # File Search Section
        file_frame = ctk.CTkFrame(self.tab_tools)
        file_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        file_frame.grid_columnconfigure(1, weight=1)

        file_title = ctk.CTkLabel(
            file_frame,
            text="Pesquisa de Ficheiros",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        file_title.grid(row=0, column=0, columnspan=4, padx=10, pady=(10, 5), sticky="w")

        self.file_query_entry = ctk.CTkEntry(
            file_frame,
            placeholder_text="Nome do ficheiro..."
        )
        self.file_query_entry.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        self.file_path_entry = ctk.CTkEntry(
            file_frame,
            placeholder_text="Caminho (default: ~)",
            width=200
        )
        self.file_path_entry.grid(row=1, column=1, padx=5, pady=10)

        file_search_btn = ctk.CTkButton(
            file_frame,
            text="Pesquisar",
            width=100,
            command=self._on_file_search
        )
        file_search_btn.grid(row=1, column=2, padx=10, pady=10)

        # Web Search Section
        web_frame = ctk.CTkFrame(self.tab_tools)
        web_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        web_frame.grid_columnconfigure(0, weight=1)

        web_title = ctk.CTkLabel(
            web_frame,
            text="Pesquisa na Internet",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        web_title.grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="w")

        self.web_query_entry = ctk.CTkEntry(
            web_frame,
            placeholder_text="Termo de pesquisa..."
        )
        self.web_query_entry.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        web_search_btn = ctk.CTkButton(
            web_frame,
            text="Pesquisar",
            width=100,
            command=self._on_web_search
        )
        web_search_btn.grid(row=1, column=1, padx=10, pady=10)

        # Results area
        results_frame = ctk.CTkFrame(self.tab_tools)
        results_frame.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="nsew")
        results_frame.grid_columnconfigure(0, weight=1)
        results_frame.grid_rowconfigure(1, weight=1)

        results_title = ctk.CTkLabel(
            results_frame,
            text="Resultados",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        results_title.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")

        self.tools_results_textbox = ctk.CTkTextbox(
            results_frame,
            wrap="word",
            font=ctk.CTkFont(size=12)
        )
        self.tools_results_textbox.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.tools_results_textbox.insert("1.0", "Os resultados das pesquisas aparecerao aqui...")
        self.tools_results_textbox.configure(state="disabled")

    # Event handlers
    def _on_send_message(self, event=None):
        """Envia mensagem para o agente."""
        message = self.chat_entry.get().strip()
        if not message or not self.app_ref:
            return

        self.chat_entry.delete(0, "end")
        self.chat_entry.configure(state="disabled")

        self._append_to_chat(f"\n[Utilizador]: {message}\n")
        self._append_to_chat("\n[Guardian]: A pensar...\n")

        self.status_var.set("A processar...")

        def process():
            try:
                response = self.app_ref.agent.think(message)
                self.after(0, lambda: self._update_chat_response(response))
            except Exception as e:
                self.after(0, lambda: self._update_chat_response(f"Erro: {str(e)}"))

        thread = threading.Thread(target=process, daemon=True)
        thread.start()

    def _update_chat_response(self, response):
        """Atualiza a resposta no chat."""
        self.chat_textbox.configure(state="normal")

        # Get all text and remove "A pensar..."
        content = self.chat_textbox.get("1.0", "end")
        thinking_msg = "[Guardian]: A pensar...\n"
        if thinking_msg in content:
            idx = content.rfind(thinking_msg)
            if idx >= 0:
                # Calculate line position
                lines_before = content[:idx].count('\n') + 1
                self.chat_textbox.delete(f"{lines_before}.0", f"{lines_before + 1}.0")

        self.chat_textbox.configure(state="disabled")
        self._append_to_chat(f"[Guardian]: {response}\n")

        self.chat_entry.configure(state="normal")
        self.chat_entry.focus()
        self.status_var.set("Pronto")

        self._on_refresh_reasoning()

    def _on_clear_chat(self):
        """Limpa o historico de chat."""
        if self.app_ref:
            self.app_ref.agent.clear_history()

        self.chat_textbox.configure(state="normal")
        self.chat_textbox.delete("1.0", "end")
        self.chat_textbox.insert("1.0", "=== Chat limpo ===\n\nEscreve a tua mensagem abaixo...\n\n")
        self.chat_textbox.configure(state="disabled")

    def refresh_blocked_ips(self):
        """Atualiza a lista de IPs bloqueados."""
        if not self.app_ref:
            return

        # Clear existing items
        for item in self.blocked_tree.get_children():
            self.blocked_tree.delete(item)

        blocked = self.app_ref.firewall.list_blocked()

        for entry in blocked:
            status = "Permanente" if entry.get("is_permanent") else f"Expira: {entry.get('expires_at', 'N/A')}"
            self.blocked_tree.insert("", "end", values=(
                entry.get("ip", ""),
                entry.get("reason", ""),
                entry.get("blocked_at", "")[:19] if entry.get("blocked_at") else "",
                status
            ))

        # Update stats
        stats = self.app_ref.firewall.get_statistics()
        self.blocked_stats_var.set(
            f"Total: {stats['total_blocked']} | "
            f"Permanentes: {stats['permanent']} | "
            f"Temporarios: {stats['temporary']}"
        )

    def _on_block_ip(self):
        """Bloqueia um IP."""
        if not self.app_ref:
            return

        ip = self.add_ip_entry.get().strip()
        reason = self.add_reason_entry.get().strip() or "Bloqueio manual"

        if not ip:
            self.status_var.set("Erro: IP nao pode estar vazio")
            return

        result = self.app_ref.firewall.block_ip(ip, reason)

        if result["success"]:
            self.add_ip_entry.delete(0, "end")
            self.add_reason_entry.delete(0, "end")
            self.refresh_blocked_ips()
            self.status_var.set(f"IP {ip} bloqueado com sucesso")
        else:
            self.status_var.set(f"Erro: {result.get('error', 'Desconhecido')}")

    def _on_unblock_ip(self):
        """Desbloqueia o IP selecionado."""
        if not self.app_ref:
            return

        selection = self.blocked_tree.selection()
        if not selection:
            self.status_var.set("Seleciona um IP para desbloquear")
            return

        item = selection[0]
        ip = self.blocked_tree.item(item, "values")[0]

        result = self.app_ref.firewall.unblock_ip(ip)

        if result["success"]:
            self.refresh_blocked_ips()
            self.status_var.set(f"IP {ip} desbloqueado com sucesso")
        else:
            self.status_var.set(f"Erro: {result.get('error', 'Desconhecido')}")

    def _on_refresh_reasoning(self):
        """Atualiza o historico de raciocinio."""
        if not self.app_ref:
            return

        sessions = self.app_ref.reasoning_engine.list_sessions()

        self.reasoning_textbox.configure(state="normal")
        self.reasoning_textbox.delete("1.0", "end")

        if not sessions:
            self.reasoning_textbox.insert(
                "1.0",
                "Nenhuma sessao de raciocinio gravada.\n\n"
                "O raciocinio sera gravado automaticamente durante as interacoes."
            )
        else:
            text = f"=== {len(sessions)} Sessoes de Raciocinio ===\n\n"

            for session in sessions[:10]:
                text += f"Sessao: {session['session_id']}\n"
                text += f"  Passos: {session['total_steps']}\n"
                text += f"  Ficheiro: {session['file']}\n\n"

            if self.app_ref.reasoning_engine.current_session:
                text += "\n=== Sessao Atual ===\n"
                text += self.app_ref.reasoning_engine.get_reasoning_chain()

            self.reasoning_textbox.insert("1.0", text)

        self.reasoning_textbox.configure(state="disabled")

    def _on_clear_reasoning(self):
        """Limpa o historico de raciocinio."""
        if self.app_ref:
            self.app_ref.reasoning_engine.current_session = []

        self.reasoning_textbox.configure(state="normal")
        self.reasoning_textbox.delete("1.0", "end")
        self.reasoning_textbox.insert("1.0", "Historico limpo.")
        self.reasoning_textbox.configure(state="disabled")

    def _on_file_search(self):
        """Executa pesquisa de ficheiros."""
        query = self.file_query_entry.get().strip()
        path = self.file_path_entry.get().strip() or "~"

        if not query:
            self._update_tools_results("Erro: Query nao pode estar vazia")
            return

        self._update_tools_results("A pesquisar...")
        self.status_var.set("A pesquisar ficheiros...")

        def search():
            tool = FileSearchTool({})
            results = tool.search_by_name(query, path)

            output = [f"Pesquisa: '{query}' em '{path}'\n"]
            output.append(f"Encontrados: {len(results)} ficheiro(s)\n")
            output.append("-" * 50 + "\n")

            for r in results[:20]:
                if "error" in r:
                    output.append(f"Erro: {r['error']}\n")
                else:
                    output.append(f"{r.get('path', 'N/A')}\n")
                    output.append(f"  Tamanho: {r.get('size_human', 'N/A')}\n")
                    output.append(f"  Modificado: {r.get('modified', 'N/A')}\n\n")

            self.after(0, lambda: self._update_tools_results("".join(output)))
            self.after(0, lambda: self.status_var.set("Pesquisa concluida"))

        thread = threading.Thread(target=search, daemon=True)
        thread.start()

    def _on_web_search(self):
        """Executa pesquisa na web."""
        query = self.web_query_entry.get().strip()

        if not query:
            self._update_tools_results("Erro: Query nao pode estar vazia")
            return

        self._update_tools_results("A pesquisar na internet...")
        self.status_var.set("A pesquisar na web...")

        def search():
            tool = WebSearchTool({"max_results": 10})
            results = tool.search(query)

            output = [f"Pesquisa Web: '{query}'\n"]
            output.append("-" * 50 + "\n\n")

            for i, r in enumerate(results, 1):
                if "error" in r:
                    output.append(f"Erro: {r['error']}\n")
                else:
                    output.append(f"{i}. {r.get('title', 'N/A')}\n")
                    output.append(f"   URL: {r.get('url', 'N/A')}\n")
                    desc = r.get('description', '')[:200]
                    if desc:
                        output.append(f"   {desc}...\n")
                    output.append("\n")

            self.after(0, lambda: self._update_tools_results("".join(output)))
            self.after(0, lambda: self.status_var.set("Pesquisa concluida"))

        thread = threading.Thread(target=search, daemon=True)
        thread.start()

    def _update_tools_results(self, text):
        """Atualiza a area de resultados."""
        self.tools_results_textbox.configure(state="normal")
        self.tools_results_textbox.delete("1.0", "end")
        self.tools_results_textbox.insert("1.0", text)
        self.tools_results_textbox.configure(state="disabled")


def run_app():
    """Funcao para executar a aplicacao."""
    app = GuardianApp()
    app.run()
    return 0


if __name__ == "__main__":
    run_app()
