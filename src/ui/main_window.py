"""
Guardian UI - Interface GTK4 Principal
Aplicação com separadores (tabs) para diferentes funcionalidades
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib, Pango, Gdk
import threading
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.llm_agent import GuardianAgent
from agent.reasoning import ReasoningEngine
from tools.firewall import FirewallManager
from tools.file_search import FileSearchTool
from tools.web_search import WebSearchTool


class GuardianApp(Adw.Application):
    """Aplicação principal Guardian."""

    def __init__(self):
        super().__init__(application_id='com.guardian.agent')
        self.connect('activate', self.on_activate)

        # Initialize components
        self.config = self._load_config()
        self.agent = None
        self.firewall = None
        self.reasoning_engine = None

    def _load_config(self):
        """Carrega configuração."""
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

    def on_activate(self, app):
        """Ativa a aplicação."""
        # Initialize components
        self.firewall = FirewallManager(self.config.get("firewall", {}))
        self.reasoning_engine = ReasoningEngine(self.config.get("reasoning", {}))

        # Setup tools for agent
        tools = {
            "file_search": self._tool_file_search,
            "web_search": self._tool_web_search,
            "block_ip": self._tool_block_ip,
            "unblock_ip": self._tool_unblock_ip,
            "list_blocked_ips": self._tool_list_blocked_ips,
        }

        self.agent = GuardianAgent(self.config, tools)
        self.agent.initialize()

        # Create main window
        self.win = MainWindow(application=app)
        self.win.set_app(self)
        self.win.present()

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
            # Update UI
            GLib.idle_add(self.win.refresh_blocked_ips)
            return f"IP {ip} bloqueado com sucesso."
        return f"Erro: {result.get('error', 'Desconhecido')}"

    def _tool_unblock_ip(self, ip: str) -> str:
        """Tool wrapper for unblocking IP."""
        result = self.firewall.unblock_ip(ip)
        if result["success"]:
            GLib.idle_add(self.win.refresh_blocked_ips)
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


class MainWindow(Adw.ApplicationWindow):
    """Janela principal com separadores."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app_ref = None

        self.set_title("Guardian - Agente LLM Offline")
        self.set_default_size(1200, 800)

        # Apply dark theme
        style_manager = Adw.StyleManager.get_default()
        style_manager.set_color_scheme(Adw.ColorScheme.PREFER_DARK)

        # Main layout
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(self.main_box)

        # Header bar
        self.header = Adw.HeaderBar()
        self.main_box.append(self.header)

        # Title
        title_label = Gtk.Label(label="Guardian")
        title_label.add_css_class("title-1")
        self.header.set_title_widget(title_label)

        # Menu button
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        self.header.pack_end(menu_button)

        # Create notebook (tabs)
        self.notebook = Gtk.Notebook()
        self.notebook.set_vexpand(True)
        self.main_box.append(self.notebook)

        # Create tabs
        self._create_chat_tab()
        self._create_blocked_ips_tab()
        self._create_reasoning_tab()
        self._create_tools_tab()

        # Status bar
        self.status_bar = Gtk.Label(label="Pronto")
        self.status_bar.set_halign(Gtk.Align.START)
        self.status_bar.set_margin_start(10)
        self.status_bar.set_margin_end(10)
        self.status_bar.set_margin_top(5)
        self.status_bar.set_margin_bottom(5)
        self.main_box.append(self.status_bar)

    def set_app(self, app):
        """Define referência para a aplicação."""
        self.app_ref = app
        self.refresh_blocked_ips()

    def _create_chat_tab(self):
        """Cria a tab de chat com o agente."""
        chat_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        chat_box.set_margin_start(10)
        chat_box.set_margin_end(10)
        chat_box.set_margin_top(10)
        chat_box.set_margin_bottom(10)

        # Chat history (scrollable)
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self.chat_view = Gtk.TextView()
        self.chat_view.set_editable(False)
        self.chat_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.chat_view.set_left_margin(10)
        self.chat_view.set_right_margin(10)
        self.chat_view.set_top_margin(10)
        self.chat_buffer = self.chat_view.get_buffer()

        # Add welcome message
        self.chat_buffer.set_text(
            "=== Guardian - Agente LLM Offline ===\n\n"
            "Olá! Sou o Guardian, o teu assistente AI local.\n"
            "Posso ajudar-te com:\n"
            "  - Pesquisar ficheiros no sistema\n"
            "  - Pesquisar na internet\n"
            "  - Gerir o firewall (bloquear/desbloquear IPs)\n"
            "  - Raciocinar sobre problemas complexos\n\n"
            "Escreve a tua mensagem abaixo...\n\n"
        )

        scroll.set_child(self.chat_view)
        chat_box.append(scroll)

        # Input area
        input_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)

        self.chat_entry = Gtk.Entry()
        self.chat_entry.set_hexpand(True)
        self.chat_entry.set_placeholder_text("Escreve a tua mensagem...")
        self.chat_entry.connect("activate", self._on_send_message)

        send_button = Gtk.Button(label="Enviar")
        send_button.add_css_class("suggested-action")
        send_button.connect("clicked", self._on_send_message)

        clear_button = Gtk.Button(label="Limpar")
        clear_button.connect("clicked", self._on_clear_chat)

        input_box.append(self.chat_entry)
        input_box.append(send_button)
        input_box.append(clear_button)

        chat_box.append(input_box)

        # Add tab
        tab_label = Gtk.Label(label="Chat")
        self.notebook.append_page(chat_box, tab_label)

    def _create_blocked_ips_tab(self):
        """Cria a tab de IPs bloqueados."""
        blocked_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        blocked_box.set_margin_start(10)
        blocked_box.set_margin_end(10)
        blocked_box.set_margin_top(10)
        blocked_box.set_margin_bottom(10)

        # Header
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        title = Gtk.Label(label="IPs Bloqueados")
        title.add_css_class("title-2")
        title.set_halign(Gtk.Align.START)
        title.set_hexpand(True)

        refresh_btn = Gtk.Button(label="Atualizar")
        refresh_btn.connect("clicked", lambda _: self.refresh_blocked_ips())

        header_box.append(title)
        header_box.append(refresh_btn)
        blocked_box.append(header_box)

        # Stats
        self.blocked_stats = Gtk.Label(label="Total: 0 | Permanentes: 0 | Temporários: 0")
        self.blocked_stats.set_halign(Gtk.Align.START)
        blocked_box.append(self.blocked_stats)

        # Separator
        blocked_box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        # List of blocked IPs (scrollable)
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        # Create list store and tree view
        # Columns: IP, Reason, Blocked At, Status
        self.blocked_list_store = Gtk.ListStore(str, str, str, str)
        self.blocked_tree_view = Gtk.TreeView(model=self.blocked_list_store)

        # Create columns
        columns = [
            ("IP", 0, 150),
            ("Motivo", 1, 250),
            ("Bloqueado em", 2, 180),
            ("Status", 3, 120)
        ]

        for title, idx, width in columns:
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer, text=idx)
            column.set_min_width(width)
            column.set_resizable(True)
            self.blocked_tree_view.append_column(column)

        scroll.set_child(self.blocked_tree_view)
        blocked_box.append(scroll)

        # Actions
        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        # Add IP
        self.add_ip_entry = Gtk.Entry()
        self.add_ip_entry.set_placeholder_text("IP a bloquear (ex: 192.168.1.100)")
        self.add_ip_entry.set_hexpand(True)

        self.add_reason_entry = Gtk.Entry()
        self.add_reason_entry.set_placeholder_text("Motivo")
        self.add_reason_entry.set_width_chars(20)

        add_btn = Gtk.Button(label="Bloquear IP")
        add_btn.add_css_class("destructive-action")
        add_btn.connect("clicked", self._on_block_ip)

        unblock_btn = Gtk.Button(label="Desbloquear Selecionado")
        unblock_btn.connect("clicked", self._on_unblock_ip)

        actions_box.append(self.add_ip_entry)
        actions_box.append(self.add_reason_entry)
        actions_box.append(add_btn)
        actions_box.append(unblock_btn)

        blocked_box.append(actions_box)

        # Add tab with icon
        tab_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        tab_icon = Gtk.Image.new_from_icon_name("network-server-symbolic")
        tab_label = Gtk.Label(label="IPs Bloqueados")
        tab_box.append(tab_icon)
        tab_box.append(tab_label)

        self.notebook.append_page(blocked_box, tab_box)

    def _create_reasoning_tab(self):
        """Cria a tab de histórico de raciocínio."""
        reasoning_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        reasoning_box.set_margin_start(10)
        reasoning_box.set_margin_end(10)
        reasoning_box.set_margin_top(10)
        reasoning_box.set_margin_bottom(10)

        # Header
        header = Gtk.Label(label="Histórico de Raciocínio")
        header.add_css_class("title-2")
        header.set_halign(Gtk.Align.START)
        reasoning_box.append(header)

        # Description
        desc = Gtk.Label(
            label="O Guardian grava todo o seu processo de raciocínio para análise posterior."
        )
        desc.set_halign(Gtk.Align.START)
        desc.set_wrap(True)
        reasoning_box.append(desc)

        reasoning_box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        # Sessions list
        sessions_scroll = Gtk.ScrolledWindow()
        sessions_scroll.set_vexpand(True)

        self.reasoning_view = Gtk.TextView()
        self.reasoning_view.set_editable(False)
        self.reasoning_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.reasoning_view.set_left_margin(10)
        self.reasoning_view.set_right_margin(10)
        self.reasoning_buffer = self.reasoning_view.get_buffer()
        self.reasoning_buffer.set_text("Nenhuma sessão de raciocínio ainda.\n\nO raciocínio será gravado automaticamente durante as interações.")

        sessions_scroll.set_child(self.reasoning_view)
        reasoning_box.append(sessions_scroll)

        # Buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        refresh_btn = Gtk.Button(label="Atualizar")
        refresh_btn.connect("clicked", self._on_refresh_reasoning)

        clear_btn = Gtk.Button(label="Limpar Histórico")
        clear_btn.connect("clicked", self._on_clear_reasoning)

        btn_box.append(refresh_btn)
        btn_box.append(clear_btn)
        reasoning_box.append(btn_box)

        # Add tab
        tab_label = Gtk.Label(label="Raciocínio")
        self.notebook.append_page(reasoning_box, tab_label)

    def _create_tools_tab(self):
        """Cria a tab de ferramentas."""
        tools_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        tools_box.set_margin_start(10)
        tools_box.set_margin_end(10)
        tools_box.set_margin_top(10)
        tools_box.set_margin_bottom(10)

        # Header
        header = Gtk.Label(label="Ferramentas")
        header.add_css_class("title-2")
        header.set_halign(Gtk.Align.START)
        tools_box.append(header)

        # File Search Section
        file_frame = Gtk.Frame(label="Pesquisa de Ficheiros")
        file_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        file_box.set_margin_start(10)
        file_box.set_margin_end(10)
        file_box.set_margin_top(10)
        file_box.set_margin_bottom(10)

        file_input_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)

        self.file_query_entry = Gtk.Entry()
        self.file_query_entry.set_placeholder_text("Nome do ficheiro...")
        self.file_query_entry.set_hexpand(True)

        self.file_path_entry = Gtk.Entry()
        self.file_path_entry.set_placeholder_text("Caminho (default: ~)")
        self.file_path_entry.set_width_chars(20)

        file_search_btn = Gtk.Button(label="Pesquisar")
        file_search_btn.connect("clicked", self._on_file_search)

        file_input_box.append(self.file_query_entry)
        file_input_box.append(self.file_path_entry)
        file_input_box.append(file_search_btn)

        file_box.append(file_input_box)
        file_frame.set_child(file_box)
        tools_box.append(file_frame)

        # Web Search Section
        web_frame = Gtk.Frame(label="Pesquisa na Internet")
        web_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        web_box.set_margin_start(10)
        web_box.set_margin_end(10)
        web_box.set_margin_top(10)
        web_box.set_margin_bottom(10)

        web_input_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)

        self.web_query_entry = Gtk.Entry()
        self.web_query_entry.set_placeholder_text("Termo de pesquisa...")
        self.web_query_entry.set_hexpand(True)

        web_search_btn = Gtk.Button(label="Pesquisar")
        web_search_btn.connect("clicked", self._on_web_search)

        web_input_box.append(self.web_query_entry)
        web_input_box.append(web_search_btn)

        web_box.append(web_input_box)
        web_frame.set_child(web_box)
        tools_box.append(web_frame)

        # Results area
        results_frame = Gtk.Frame(label="Resultados")
        results_scroll = Gtk.ScrolledWindow()
        results_scroll.set_vexpand(True)
        results_scroll.set_min_content_height(200)

        self.tools_results_view = Gtk.TextView()
        self.tools_results_view.set_editable(False)
        self.tools_results_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.tools_results_view.set_left_margin(10)
        self.tools_results_buffer = self.tools_results_view.get_buffer()
        self.tools_results_buffer.set_text("Os resultados das pesquisas aparecerão aqui...")

        results_scroll.set_child(self.tools_results_view)
        results_frame.set_child(results_scroll)
        tools_box.append(results_frame)

        # Add tab
        tab_label = Gtk.Label(label="Ferramentas")
        self.notebook.append_page(tools_box, tab_label)

    # Event handlers
    def _on_send_message(self, widget):
        """Envia mensagem para o agente."""
        message = self.chat_entry.get_text().strip()
        if not message or not self.app_ref:
            return

        self.chat_entry.set_text("")
        self.chat_entry.set_sensitive(False)

        # Add user message to chat
        end_iter = self.chat_buffer.get_end_iter()
        self.chat_buffer.insert(end_iter, f"\n[Utilizador]: {message}\n")
        self.chat_buffer.insert(end_iter, "\n[Guardian]: A pensar...\n")

        self.status_bar.set_text("A processar...")

        # Process in background thread
        def process():
            try:
                response = self.app_ref.agent.think(message)
                GLib.idle_add(self._update_chat_response, response)
            except Exception as e:
                GLib.idle_add(self._update_chat_response, f"Erro: {str(e)}")

        thread = threading.Thread(target=process, daemon=True)
        thread.start()

    def _update_chat_response(self, response):
        """Atualiza a resposta no chat."""
        # Remove "A pensar..."
        end_iter = self.chat_buffer.get_end_iter()
        start_iter = self.chat_buffer.get_iter_at_offset(
            self.chat_buffer.get_char_count() - len("[Guardian]: A pensar...\n")
        )
        self.chat_buffer.delete(start_iter, end_iter)

        # Add response
        end_iter = self.chat_buffer.get_end_iter()
        self.chat_buffer.insert(end_iter, f"[Guardian]: {response}\n")

        # Scroll to bottom
        self.chat_view.scroll_to_iter(self.chat_buffer.get_end_iter(), 0, False, 0, 0)

        self.chat_entry.set_sensitive(True)
        self.chat_entry.grab_focus()
        self.status_bar.set_text("Pronto")

        # Update reasoning
        self._on_refresh_reasoning(None)

    def _on_clear_chat(self, widget):
        """Limpa o histórico de chat."""
        if self.app_ref:
            self.app_ref.agent.clear_history()
        self.chat_buffer.set_text(
            "=== Chat limpo ===\n\nEscreve a tua mensagem abaixo...\n\n"
        )

    def refresh_blocked_ips(self):
        """Atualiza a lista de IPs bloqueados."""
        if not self.app_ref:
            return

        self.blocked_list_store.clear()
        blocked = self.app_ref.firewall.list_blocked()

        for entry in blocked:
            status = "Permanente" if entry.get("is_permanent") else f"Expira: {entry.get('expires_at', 'N/A')}"
            self.blocked_list_store.append([
                entry.get("ip", ""),
                entry.get("reason", ""),
                entry.get("blocked_at", "")[:19] if entry.get("blocked_at") else "",
                status
            ])

        # Update stats
        stats = self.app_ref.firewall.get_statistics()
        self.blocked_stats.set_text(
            f"Total: {stats['total_blocked']} | "
            f"Permanentes: {stats['permanent']} | "
            f"Temporários: {stats['temporary']}"
        )

    def _on_block_ip(self, widget):
        """Bloqueia um IP."""
        if not self.app_ref:
            return

        ip = self.add_ip_entry.get_text().strip()
        reason = self.add_reason_entry.get_text().strip() or "Bloqueio manual"

        if not ip:
            self.status_bar.set_text("Erro: IP não pode estar vazio")
            return

        result = self.app_ref.firewall.block_ip(ip, reason)

        if result["success"]:
            self.add_ip_entry.set_text("")
            self.add_reason_entry.set_text("")
            self.refresh_blocked_ips()
            self.status_bar.set_text(f"IP {ip} bloqueado com sucesso")
        else:
            self.status_bar.set_text(f"Erro: {result.get('error', 'Desconhecido')}")

    def _on_unblock_ip(self, widget):
        """Desbloqueia o IP selecionado."""
        if not self.app_ref:
            return

        selection = self.blocked_tree_view.get_selection()
        model, iter = selection.get_selected()

        if iter is None:
            self.status_bar.set_text("Seleciona um IP para desbloquear")
            return

        ip = model.get_value(iter, 0)
        result = self.app_ref.firewall.unblock_ip(ip)

        if result["success"]:
            self.refresh_blocked_ips()
            self.status_bar.set_text(f"IP {ip} desbloqueado com sucesso")
        else:
            self.status_bar.set_text(f"Erro: {result.get('error', 'Desconhecido')}")

    def _on_refresh_reasoning(self, widget):
        """Atualiza o histórico de raciocínio."""
        if not self.app_ref:
            return

        sessions = self.app_ref.reasoning_engine.list_sessions()

        if not sessions:
            self.reasoning_buffer.set_text(
                "Nenhuma sessão de raciocínio gravada.\n\n"
                "O raciocínio será gravado automaticamente durante as interações."
            )
            return

        text = f"=== {len(sessions)} Sessões de Raciocínio ===\n\n"

        for session in sessions[:10]:  # Show last 10
            text += f"Sessão: {session['session_id']}\n"
            text += f"  Passos: {session['total_steps']}\n"
            text += f"  Ficheiro: {session['file']}\n\n"

        # Show current session if available
        if self.app_ref.reasoning_engine.current_session:
            text += "\n=== Sessão Atual ===\n"
            text += self.app_ref.reasoning_engine.get_reasoning_chain()

        self.reasoning_buffer.set_text(text)

    def _on_clear_reasoning(self, widget):
        """Limpa o histórico de raciocínio."""
        if self.app_ref:
            self.app_ref.reasoning_engine.current_session = []
        self.reasoning_buffer.set_text("Histórico limpo.")

    def _on_file_search(self, widget):
        """Executa pesquisa de ficheiros."""
        query = self.file_query_entry.get_text().strip()
        path = self.file_path_entry.get_text().strip() or "~"

        if not query:
            self.tools_results_buffer.set_text("Erro: Query não pode estar vazia")
            return

        self.tools_results_buffer.set_text("A pesquisar...")
        self.status_bar.set_text("A pesquisar ficheiros...")

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

            GLib.idle_add(self.tools_results_buffer.set_text, "".join(output))
            GLib.idle_add(self.status_bar.set_text, "Pesquisa concluída")

        thread = threading.Thread(target=search, daemon=True)
        thread.start()

    def _on_web_search(self, widget):
        """Executa pesquisa na web."""
        query = self.web_query_entry.get_text().strip()

        if not query:
            self.tools_results_buffer.set_text("Erro: Query não pode estar vazia")
            return

        self.tools_results_buffer.set_text("A pesquisar na internet...")
        self.status_bar.set_text("A pesquisar na web...")

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

            GLib.idle_add(self.tools_results_buffer.set_text, "".join(output))
            GLib.idle_add(self.status_bar.set_text, "Pesquisa concluída")

        thread = threading.Thread(target=search, daemon=True)
        thread.start()


def run_app():
    """Função para executar a aplicação."""
    app = GuardianApp()
    return app.run(None)


if __name__ == "__main__":
    run_app()
