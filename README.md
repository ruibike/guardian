# Guardian - Agente LLM Offline

Um agente AI local otimizado para sistemas Ubuntu com 8GB de RAM.

## Funcionalidades

- **Raciocínio Autónomo**: O Guardian pensa passo a passo e grava todo o processo de raciocínio
- **Pesquisa de Ficheiros**: Encontra ficheiros no sistema por nome ou conteúdo
- **Pesquisa na Internet**: Usa DuckDuckGo para pesquisas privadas
- **Gestão de Firewall**: Bloqueia e desbloqueia IPs suspeitos
- **Interface Gráfica**: UI moderna com GTK4/Adwaita

## Requisitos

- Ubuntu 20.04+ (ou derivados)
- Python 3.9+
- 8GB RAM (mínimo recomendado)
- GTK4 e libadwaita (para interface gráfica)

## Instalação

### 1. Dependências do Sistema

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3-pip python3-gi python3-gi-cairo gir1.2-gtk-4.0 libadwaita-1-dev
```

### 2. Dependências Python

```bash
pip install -r requirements.txt
```

### 3. Modelo LLM (Opcional)

Para usar um modelo LLM local:

```bash
mkdir -p ~/.local/share/guardian/models
cd ~/.local/share/guardian/models

# Mistral 7B Q4 (~4GB, bom equilíbrio qualidade/RAM)
wget https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf

# OU modelos mais pequenos para sistemas com menos RAM:
# Phi-2 (~1.6GB)
# wget https://huggingface.co/TheBloke/phi-2-GGUF/resolve/main/phi-2.Q4_K_M.gguf

# TinyLlama (~700MB)
# wget https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf
```

## Uso

### Interface Gráfica

```bash
python main.py
```

### Modo CLI

```bash
python main.py --cli
```

### Verificar Sistema

```bash
python main.py --check
```

## Comandos CLI

| Comando | Descrição |
|---------|-----------|
| `/quit`, `/exit` | Sair |
| `/clear` | Limpar histórico |
| `/blocked` | Listar IPs bloqueados |
| `/block <ip>` | Bloquear IP |
| `/unblock <ip>` | Desbloquear IP |
| `/search <query>` | Pesquisar ficheiros |
| `/web <query>` | Pesquisar na internet |
| `/help` | Mostrar ajuda |

## Estrutura do Projeto

```
guardian/
├── main.py              # Ponto de entrada
├── config.yaml          # Configuração
├── requirements.txt     # Dependências Python
├── src/
│   ├── agent/
│   │   ├── llm_agent.py    # Agente LLM principal
│   │   └── reasoning.py     # Motor de raciocínio
│   ├── tools/
│   │   ├── file_search.py   # Pesquisa de ficheiros
│   │   ├── web_search.py    # Pesquisa na internet
│   │   └── firewall.py      # Gestão de IPs
│   └── ui/
│       └── main_window.py   # Interface GTK4
├── data/
│   ├── reasoning/       # Logs de raciocínio
│   └── blocked_ips/     # Lista de IPs bloqueados
└── logs/                # Logs da aplicação
```

## Configuração

Edita `config.yaml` para personalizar:

```yaml
llm:
  model_path: "~/.local/share/guardian/models/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
  n_ctx: 2048          # Janela de contexto
  n_threads: 4         # Threads CPU
  n_gpu_layers: 0      # 0 para CPU-only

reasoning:
  save_to_file: true   # Gravar raciocínio
  max_steps: 10        # Máximo de passos

firewall:
  enabled: true
  auto_block_suspicious: true
```

## Otimização para 8GB RAM

- Usa quantização Q4_K_M para modelos (4-bit)
- Contexto limitado a 2048 tokens
- Sem GPU layers (usa CPU)
- Modelo Mistral 7B usa ~4GB de RAM

Para sistemas com menos RAM:
- Usa Phi-2 ou TinyLlama
- Reduz `n_ctx` para 1024
- Reduz `n_batch` para 128

## Licença

MIT License
