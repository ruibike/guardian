# Guardian - Agente LLM Offline

Um agente AI local otimizado para sistemas Ubuntu com 8GB de RAM.

## Funcionalidades

- **Raciocinio Autonomo**: O Guardian pensa passo a passo e grava todo o processo de raciocinio
- **Pesquisa de Ficheiros**: Encontra ficheiros no sistema por nome ou conteudo
- **Pesquisa na Internet**: Usa DuckDuckGo para pesquisas privadas
- **Gestao de Firewall**: Bloqueia e desbloqueia IPs suspeitos
- **Interface Grafica**: UI moderna com CustomTkinter (Dark Mode)

## Requisitos

- Ubuntu 18.04+ / Debian 10+ (ou qualquer distribuicao Linux)
- Python 3.8+
- 8GB RAM (minimo recomendado)

## Instalacao

### Instalacao Rapida (Recomendada)

```bash
# Clone o repositorio
git clone https://github.com/seuusuario/Agent1.git
cd Agent1

# Crie um ambiente virtual (opcional mas recomendado)
python3 -m venv venv
source venv/bin/activate

# Instale as dependencias
pip install -r requirements.txt
```

Isso e tudo! Nao precisa de `apt install` nem headers de sistema.

### Modelo LLM (Opcional)

Para usar um modelo LLM local:

```bash
mkdir -p ~/.local/share/guardian/models
cd ~/.local/share/guardian/models

# Mistral 7B Q4 (~4GB, bom equilibrio qualidade/RAM)
wget https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf

# OU modelos mais pequenos para sistemas com menos RAM:
# Phi-2 (~1.6GB)
# wget https://huggingface.co/TheBloke/phi-2-GGUF/resolve/main/phi-2.Q4_K_M.gguf

# TinyLlama (~700MB)
# wget https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf
```

## Uso

### Interface Grafica

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

| Comando | Descricao |
|---------|-----------|
| `/quit`, `/exit` | Sair |
| `/clear` | Limpar historico |
| `/blocked` | Listar IPs bloqueados |
| `/block <ip>` | Bloquear IP |
| `/unblock <ip>` | Desbloquear IP |
| `/search <query>` | Pesquisar ficheiros |
| `/web <query>` | Pesquisar na internet |
| `/scan` | Analisar conexoes de rede |
| `/suspicious` | Mostrar IPs suspeitos |
| `/help` | Mostrar ajuda |

## Estrutura do Projeto

```
guardian/
├── main.py              # Ponto de entrada
├── config.yaml          # Configuracao
├── requirements.txt     # Dependencias Python
├── src/
│   ├── agent/
│   │   ├── llm_agent.py    # Agente LLM principal
│   │   └── reasoning.py     # Motor de raciocinio
│   ├── tools/
│   │   ├── file_search.py   # Pesquisa de ficheiros
│   │   ├── web_search.py    # Pesquisa na internet
│   │   ├── network_monitor.py # Monitor de rede
│   │   └── firewall.py      # Gestao de IPs
│   └── ui/
│       └── main_window.py   # Interface CustomTkinter
├── data/
│   ├── reasoning/       # Logs de raciocinio
│   └── blocked_ips/     # Lista de IPs bloqueados
└── logs/                # Logs da aplicacao
```

## Configuracao

Edita `config.yaml` para personalizar:

```yaml
llm:
  model_path: "~/.local/share/guardian/models/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
  n_ctx: 2048          # Janela de contexto
  n_threads: 4         # Threads CPU
  n_gpu_layers: 0      # 0 para CPU-only

reasoning:
  save_to_file: true   # Gravar raciocinio
  max_steps: 10        # Maximo de passos

firewall:
  enabled: true
  auto_block_suspicious: true
```

## Otimizacao para 8GB RAM

- Usa quantizacao Q4_K_M para modelos (4-bit)
- Contexto limitado a 2048 tokens
- Sem GPU layers (usa CPU)
- Modelo Mistral 7B usa ~4GB de RAM

Para sistemas com menos RAM:
- Usa Phi-2 ou TinyLlama
- Reduz `n_ctx` para 1024
- Reduz `n_batch` para 128

## Portabilidade

Este projeto foi migrado de GTK4/PyGObject para CustomTkinter para garantir:
- **Instalacao Universal**: Funciona apenas com `pip install`
- **Sem dependencias de sistema**: Nao precisa de `apt install` nem compilacao
- **Compatibilidade**: Ubuntu 18.04+, Debian 10+, e outras distribuicoes Linux
- **Visual Moderno**: Tema escuro arredondado semelhante ao GNOME/Libadwaita

## Licenca

MIT License
