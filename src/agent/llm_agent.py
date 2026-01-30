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

# Import instructions
try:
    from .instructions import get_system_prompt, get_help_message, get_task_prompt
except ImportError:
    # Fallback if instructions not available
    def get_system_prompt():
        return "Tu és o Guardian, um agente AI autónomo."
    def get_help_message(topic="welcome"):
        return "Guardian - Agente LLM Offline"
    def get_task_prompt(task):
        return ""


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

        # Load system prompt from instructions
        self.system_prompt = get_system_prompt()

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

        # Bloquear IP
        if "ip" in message_lower and ("bloquear" in message_lower or "block" in message_lower):
            ip_match = re.search(r'\d+\.\d+\.\d+\.\d+', user_message)
            if ip_match:
                ip = ip_match.group()
                return f"""## Raciocínio do Guardian

### Passo 1: OBSERVAR
O utilizador pediu para bloquear o IP {ip}.

### Passo 2: ANALISAR
- IP fornecido: {ip}
- Verificar se é um IP válido: ✓
- Verificar se não é IP local (127.x.x.x, 192.168.x.x): {"⚠️ É IP privado!" if ip.startswith(("127.", "192.168.", "10.")) else "✓ É IP público"}

### Passo 3: EXECUTAR
Vou adicionar este IP à lista de bloqueio.

[TOOL:block_ip]{{"ip": "{ip}", "reason": "Bloqueio manual pelo utilizador"}}[/TOOL]

### Passo 4: REPORTAR
O IP {ip} foi adicionado à lista de bloqueio do Guardian.
Podes ver todos os IPs bloqueados no separador "IPs Bloqueados" ou usando `/blocked`."""

        # Desbloquear IP
        if "ip" in message_lower and ("desbloquear" in message_lower or "unblock" in message_lower):
            ip_match = re.search(r'\d+\.\d+\.\d+\.\d+', user_message)
            if ip_match:
                ip = ip_match.group()
                return f"""## Raciocínio do Guardian

### Passo 1: OBSERVAR
O utilizador quer desbloquear o IP {ip}.

### Passo 2: EXECUTAR
[TOOL:unblock_ip]{{"ip": "{ip}"}}[/TOOL]

### Passo 3: REPORTAR
O IP {ip} foi removido da lista de bloqueio."""

        # Listar IPs bloqueados
        if "bloqueados" in message_lower or "blocked" in message_lower or "lista" in message_lower:
            return """## Raciocínio do Guardian

### Passo 1: OBSERVAR
O utilizador quer ver os IPs bloqueados.

### Passo 2: EXECUTAR
Vou consultar a lista de firewall.

[TOOL:list_blocked_ips]{}[/TOOL]

### Passo 3: REPORTAR
Acima está a lista de todos os IPs atualmente bloqueados.
Podes também ver esta informação no separador "IPs Bloqueados" da interface."""

        # Pesquisa de ficheiros
        if ("pesquis" in message_lower or "search" in message_lower or "encontr" in message_lower or "procur" in message_lower) and \
           ("ficheiro" in message_lower or "file" in message_lower or "arquivo" in message_lower):
            # Extrair query se possível
            query = "config"
            words = user_message.split()
            for i, word in enumerate(words):
                if word.lower() in ["ficheiro", "file", "arquivo", "chamado", "nome"]:
                    if i + 1 < len(words):
                        query = words[i + 1].strip("\"'")
                        break

            return f"""## Raciocínio do Guardian

### Passo 1: OBSERVAR
O utilizador quer pesquisar ficheiros no sistema.

### Passo 2: ANALISAR
- Termo de pesquisa identificado: "{query}"
- Vou pesquisar no diretório home por defeito

### Passo 3: EXECUTAR
[TOOL:file_search]{{"query": "{query}", "path": "~"}}[/TOOL]

### Passo 4: REPORTAR
Os resultados da pesquisa estão acima.
Dica: Podes especificar um caminho diferente, ex: "pesquisa config em /etc" """

        # Pesquisa na internet
        if "pesquis" in message_lower or "search" in message_lower or "internet" in message_lower or "web" in message_lower:
            # Extrair query
            query = user_message
            for prefix in ["pesquisa", "procura", "search", "pesquisar", "procurar"]:
                if prefix in message_lower:
                    idx = message_lower.find(prefix) + len(prefix)
                    query = user_message[idx:].strip()
                    break

            return f"""## Raciocínio do Guardian

### Passo 1: OBSERVAR
O utilizador quer pesquisar na internet.

### Passo 2: ANALISAR
- Termo de pesquisa: "{query}"
- Vou usar DuckDuckGo para manter privacidade

### Passo 3: EXECUTAR
[TOOL:web_search]{{"query": "{query}"}}[/TOOL]

### Passo 4: REPORTAR
Os resultados da pesquisa web estão acima."""

        # Scan de rede
        if "rede" in message_lower or "network" in message_lower or "conexões" in message_lower or "conexoes" in message_lower:
            return """## Raciocínio do Guardian

### Passo 1: OBSERVAR
O utilizador quer analisar a rede/conexões.

### Passo 2: ANALISAR
Vou verificar:
- Conexões ativas
- IPs externos
- Portas suspeitas
- Padrões de ataque

### Passo 3: EXECUTAR
[TOOL:scan_network]{}[/TOOL]

### Passo 4: REPORTAR
A análise de rede está completa. Se foram encontrados IPs suspeitos,
considera bloqueá-los usando: `/block <ip>`"""

        # Segurança/scan
        if "segurança" in message_lower or "security" in message_lower or "scan" in message_lower or "verificar" in message_lower:
            return """## Raciocínio do Guardian

### Passo 1: OBSERVAR
O utilizador quer uma análise de segurança.

### Passo 2: PLANEAR
Vou verificar:
1. Conexões de rede suspeitas
2. IPs atualmente bloqueados
3. Recomendar ações

### Passo 3: EXECUTAR
[TOOL:scan_network]{}[/TOOL]

[TOOL:list_blocked_ips]{}[/TOOL]

### Passo 4: REPORTAR
Análise de segurança completa.
Recomendações baseadas nos resultados acima:
- Bloqueia IPs suspeitos identificados
- Verifica logs de autenticação em /var/log/auth.log
- Mantém o sistema atualizado com: sudo apt update && sudo apt upgrade"""

        # Ajuda
        if "ajuda" in message_lower or "help" in message_lower or "comandos" in message_lower:
            return get_help_message("commands")

        # Sobre
        if "sobre" in message_lower or "about" in message_lower or "quem" in message_lower:
            return get_help_message("about")

        # Resposta genérica
        return f"""## Raciocínio do Guardian

### Passo 1: OBSERVAR
Recebi a mensagem: "{user_message}"

### Passo 2: ANALISAR
A analisar o pedido para determinar a melhor forma de ajudar...

### Passo 3: RESPONDER
Olá! Sou o **Guardian**, o teu agente AI local de segurança.

Posso ajudar-te com:
- **Pesquisar ficheiros**: "pesquisa ficheiro config"
- **Pesquisar na web**: "pesquisa na internet como configurar firewall"
- **Bloquear IPs**: "bloqueia o IP 1.2.3.4"
- **Ver IPs bloqueados**: "mostra IPs bloqueados"
- **Analisar rede**: "verifica conexões de rede"
- **Scan de segurança**: "faz um scan de segurança"

**Comandos rápidos:**
- `/block <ip>` - Bloquear IP
- `/unblock <ip>` - Desbloquear IP
- `/blocked` - Listar IPs bloqueados
- `/search <query>` - Pesquisar ficheiros
- `/web <query>` - Pesquisar na internet
- `/help` - Ver todos os comandos

Em que posso ajudar hoje?"""

    def get_reasoning_history(self) -> List[Dict[str, Any]]:
        """Retorna o histórico de raciocínio."""
        return self.reasoning_log

    def clear_history(self):
        """Limpa o histórico de conversação."""
        self.conversation_history = []
        self.reasoning_log = []
