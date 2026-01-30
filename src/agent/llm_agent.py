"""
Guardian LLM Agent - Offline AI Agent optimized for 8GB RAM
Raciocina autonomamente, pesquisa ficheiros e internet
"""

import os
import json
import re
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable
from pathlib import Path

try:
    from llama_cpp import Llama
    LLAMA_AVAILABLE = True
except ImportError:
    LLAMA_AVAILABLE = False


class GuardianAgent:
    """
    Agente LLM offline que raciocina autonomamente.
    Otimizado para sistemas com 8GB de RAM.
    """

    def __init__(self, config: Dict[str, Any], tools: Optional[Dict[str, Callable]] = None):
        self.config = config
        self.llm_config = config.get("llm", {})
        self.reasoning_config = config.get("reasoning", {})
        self.tools = tools or {}
        self.llm = None
        self.conversation_history = []
        self.reasoning_log = []

        # System prompt for autonomous reasoning
        self.system_prompt = """Tu és o Guardian, um agente AI autónomo a correr localmente.
Tens capacidade de:
1. RACIOCINAR passo a passo sobre problemas
2. PESQUISAR ficheiros no sistema Ubuntu
3. PESQUISAR informação na internet
4. BLOQUEAR IPs suspeitos no firewall
5. EXECUTAR comandos de sistema quando necessário

Quando recebes uma tarefa:
1. Primeiro, PENSA sobre o que precisas fazer
2. Decide que FERRAMENTAS usar
3. EXECUTA as ações necessárias
4. VERIFICA os resultados
5. REPORTA ao utilizador

Para usar ferramentas, usa o formato:
[TOOL:nome_ferramenta]{"param": "valor"}[/TOOL]

Ferramentas disponíveis:
- file_search: Pesquisa ficheiros. Params: {"query": "texto", "path": "/caminho"}
- web_search: Pesquisa na internet. Params: {"query": "pesquisa"}
- block_ip: Bloqueia um IP. Params: {"ip": "x.x.x.x", "reason": "motivo"}
- unblock_ip: Desbloqueia um IP. Params: {"ip": "x.x.x.x"}
- list_blocked_ips: Lista IPs bloqueados. Params: {}
- run_command: Executa comando. Params: {"command": "cmd"}

Pensa sempre em voz alta mostrando o teu raciocínio."""

    def initialize(self) -> bool:
        """Inicializa o modelo LLM."""
        if not LLAMA_AVAILABLE:
            print("[AVISO] llama-cpp-python não instalado. Usando modo simulado.")
            return True

        model_path = os.path.expanduser(self.llm_config.get("model_path", ""))

        if not os.path.exists(model_path):
            print(f"[AVISO] Modelo não encontrado em: {model_path}")
            print("[INFO] Para instalar um modelo compatível com 8GB RAM:")
            print("  1. Criar diretório: mkdir -p ~/.local/share/guardian/models")
            print("  2. Descarregar modelo (ex: Mistral 7B Q4):")
            print("     wget https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf")
            return False

        try:
            self.llm = Llama(
                model_path=model_path,
                n_ctx=self.llm_config.get("n_ctx", 2048),
                n_batch=self.llm_config.get("n_batch", 256),
                n_threads=self.llm_config.get("n_threads", 4),
                n_gpu_layers=self.llm_config.get("n_gpu_layers", 0),
                verbose=False
            )
            print(f"[OK] Modelo carregado: {model_path}")
            return True
        except Exception as e:
            print(f"[ERRO] Falha ao carregar modelo: {e}")
            return False

    def _build_prompt(self, user_message: str) -> str:
        """Constrói o prompt completo com histórico."""
        prompt = f"<|system|>\n{self.system_prompt}\n"

        # Add conversation history (limited to save memory)
        for msg in self.conversation_history[-6:]:
            role = msg["role"]
            content = msg["content"]
            prompt += f"<|{role}|>\n{content}\n"

        prompt += f"<|user|>\n{user_message}\n<|assistant|>\n"
        return prompt

    def _parse_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """Extrai chamadas de ferramentas da resposta."""
        tool_calls = []
        pattern = r'\[TOOL:(\w+)\](.*?)\[/TOOL\]'
        matches = re.findall(pattern, response, re.DOTALL)

        for tool_name, params_str in matches:
            try:
                params = json.loads(params_str.strip())
                tool_calls.append({
                    "tool": tool_name,
                    "params": params
                })
            except json.JSONDecodeError:
                # Try to parse as simple key=value
                tool_calls.append({
                    "tool": tool_name,
                    "params": {"raw": params_str.strip()}
                })

        return tool_calls

    def _execute_tools(self, tool_calls: List[Dict[str, Any]]) -> str:
        """Executa as ferramentas chamadas e retorna resultados."""
        results = []

        for call in tool_calls:
            tool_name = call["tool"]
            params = call["params"]

            if tool_name in self.tools:
                try:
                    result = self.tools[tool_name](**params)
                    results.append(f"[RESULTADO {tool_name}]: {result}")
                except Exception as e:
                    results.append(f"[ERRO {tool_name}]: {str(e)}")
            else:
                results.append(f"[ERRO]: Ferramenta '{tool_name}' não disponível")

        return "\n".join(results)

    def _save_reasoning(self, user_input: str, reasoning: str, response: str):
        """Guarda o raciocínio em ficheiro."""
        if not self.reasoning_config.get("save_to_file", True):
            return

        log_dir = Path(self.reasoning_config.get("log_dir", "data/reasoning"))
        log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"reasoning_{timestamp}.json"

        entry = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "reasoning_steps": reasoning,
            "final_response": response,
            "tools_used": self._parse_tool_calls(reasoning)
        }

        self.reasoning_log.append(entry)

        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(entry, f, indent=2, ensure_ascii=False)

    def think(self, user_message: str, callback: Optional[Callable] = None) -> str:
        """
        Processa uma mensagem com raciocínio autónomo.
        callback: função opcional para streaming de resposta
        """
        # Build prompt
        prompt = self._build_prompt(user_message)

        # Generate response
        if self.llm is not None:
            response_text = ""
            for token in self.llm(
                prompt,
                max_tokens=self.llm_config.get("max_tokens", 512),
                temperature=self.llm_config.get("temperature", 0.7),
                top_p=self.llm_config.get("top_p", 0.9),
                stream=True
            ):
                chunk = token["choices"][0]["text"]
                response_text += chunk
                if callback:
                    callback(chunk)
        else:
            # Simulated response for testing without model
            response_text = self._simulate_response(user_message)
            if callback:
                callback(response_text)

        # Parse and execute any tool calls
        tool_calls = self._parse_tool_calls(response_text)
        if tool_calls:
            tool_results = self._execute_tools(tool_calls)
            response_text += f"\n\n{tool_results}"

        # Update history
        self.conversation_history.append({"role": "user", "content": user_message})
        self.conversation_history.append({"role": "assistant", "content": response_text})

        # Save reasoning
        self._save_reasoning(user_message, response_text, response_text)

        return response_text

    def _simulate_response(self, user_message: str) -> str:
        """Resposta simulada quando não há modelo carregado."""
        message_lower = user_message.lower()

        if "ip" in message_lower and ("bloquear" in message_lower or "block" in message_lower):
            ip_match = re.search(r'\d+\.\d+\.\d+\.\d+', user_message)
            if ip_match:
                ip = ip_match.group()
                return f"""**Raciocínio do Guardian:**

1. O utilizador quer bloquear o IP {ip}
2. Vou verificar se é um IP válido... ✓
3. Vou usar a ferramenta de firewall

[TOOL:block_ip]{{"ip": "{ip}", "reason": "Bloqueio manual pelo utilizador"}}[/TOOL]

Pronto! O IP {ip} foi adicionado à lista de bloqueio."""

        if "pesquis" in message_lower or "search" in message_lower or "encontr" in message_lower:
            if "ficheiro" in message_lower or "file" in message_lower:
                return """**Raciocínio do Guardian:**

1. O utilizador quer pesquisar ficheiros
2. Vou usar a ferramenta de pesquisa de ficheiros

[TOOL:file_search]{"query": "config", "path": "~"}[/TOOL]

A pesquisar ficheiros no sistema..."""

            return """**Raciocínio do Guardian:**

1. O utilizador quer pesquisar na internet
2. Vou usar o DuckDuckGo para privacidade

[TOOL:web_search]{"query": "informação solicitada"}[/TOOL]

A pesquisar na web..."""

        if "bloqueados" in message_lower or "blocked" in message_lower:
            return """**Raciocínio do Guardian:**

1. O utilizador quer ver os IPs bloqueados
2. Vou consultar a lista de firewall

[TOOL:list_blocked_ips]{}[/TOOL]

A obter lista de IPs bloqueados..."""

        return f"""**Raciocínio do Guardian:**

1. Recebi a mensagem: "{user_message}"
2. A analisar o pedido...
3. Processando...

Olá! Sou o Guardian, o teu agente AI local.
Posso ajudar-te com:
- 🔍 Pesquisar ficheiros no sistema
- 🌐 Pesquisar na internet
- 🛡️ Gerir o firewall (bloquear/desbloquear IPs)
- 💭 Raciocinar sobre problemas

Em que posso ajudar?"""

    def get_reasoning_history(self) -> List[Dict[str, Any]]:
        """Retorna o histórico de raciocínio."""
        return self.reasoning_log

    def clear_history(self):
        """Limpa o histórico de conversação."""
        self.conversation_history = []
        self.reasoning_log = []
