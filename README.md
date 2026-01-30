# Guardian - Agente LLM Offline

Um agente AI local que **pensa autonomamente** usando Mistral-7B, otimizado para Ubuntu com 8GB de RAM.

## Funcionalidades

- **Cerebro LLM Local**: Usa Mistral-7B para raciocinar e tomar decisoes
- **Raciocinio Autonomo**: O Guardian pensa passo a passo (OBSERVAR -> ANALISAR -> EXECUTAR -> REPORTAR)
- **Pesquisa de Ficheiros**: Encontra ficheiros no sistema
- **Pesquisa na Internet**: Usa DuckDuckGo (privado)
- **Gestao de Firewall**: Bloqueia/desbloqueia IPs suspeitos
- **Interface Grafica**: UI moderna com tema escuro (CustomTkinter)
- **Icone no Desktop**: Abre com um clique no Ubuntu

## Requisitos

- Ubuntu 18.04+ / Debian 10+
- Python 3.8+
- **8GB RAM** (minimo) - o modelo usa ~4GB
- ~5GB espaco em disco (para o modelo)

## Instalacao Rapida (Ubuntu)

```bash
# 1. Clona o repositorio
git clone https://github.com/ruibike/guardian.git
cd guardian

# 2. Executa o instalador (faz TUDO automaticamente)
chmod +x install-ubuntu.sh
./install-ubuntu.sh
```

O instalador vai:
1. Instalar dependencias do sistema (cmake, python3-dev, etc)
2. Criar ambiente virtual Python
3. Compilar e instalar llama-cpp-python
4. Baixar o modelo Mistral-7B (~4.4GB)
5. Criar icone no Desktop

## Uso

### Via Icone (Recomendado)
Clica no icone **"Guardian AI"** no Desktop ou no menu de aplicacoes.

### Via Terminal
```bash
cd guardian
./guardian-launch.sh
```

### Modo CLI (sem interface grafica)
```bash
cd guardian
source venv/bin/activate
python main.py --cli
```

## Como o Guardian Pensa

O Guardian usa o modelo Mistral-7B como "cerebro". Quando fazes uma pergunta:

1. **OBSERVAR**: Analisa o que pediste
2. **ANALISAR**: Decide que ferramentas usar
3. **EXECUTAR**: Executa as acoes necessarias
4. **REPORTAR**: Explica o que fez e os resultados

Exemplo:
```
Tu: bloqueia o IP 192.168.1.100

Guardian:
## Raciocinio do Guardian

### Passo 1: OBSERVAR
O utilizador pediu para bloquear o IP 192.168.1.100.

### Passo 2: ANALISAR
- IP fornecido: 192.168.1.100
- Verificar se e um IP valido: OK
- E um IP privado (192.168.x.x)

### Passo 3: EXECUTAR
Vou adicionar este IP a lista de bloqueio.
[Executa ferramenta block_ip]

### Passo 4: REPORTAR
O IP 192.168.1.100 foi bloqueado com sucesso.
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
| `/help` | Mostrar ajuda |

## Estrutura do Projeto

```
guardian/
├── main.py              # Ponto de entrada
├── install-ubuntu.sh    # Instalador automatico
├── guardian-launch.sh   # Script de lancamento
├── config.yaml          # Configuracao
├── requirements.txt     # Dependencias Python
├── assets/
│   └── guardian-icon.svg  # Icone da aplicacao
├── src/
│   ├── agent/
│   │   ├── llm_agent.py    # Agente LLM (cerebro)
│   │   ├── reasoning.py     # Motor de raciocinio
│   │   └── instructions.py  # Prompts do sistema
│   ├── tools/
│   │   ├── file_search.py   # Pesquisa de ficheiros
│   │   ├── web_search.py    # Pesquisa na internet
│   │   └── firewall.py      # Gestao de IPs
│   └── ui/
│       └── main_window.py   # Interface CustomTkinter
└── data/
    ├── reasoning/       # Logs de raciocinio
    └── blocked_ips/     # Lista de IPs bloqueados
```

## Configuracao

Edita `config.yaml`:

```yaml
llm:
  model_path: "~/.local/share/guardian/models/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
  n_ctx: 2048          # Janela de contexto
  n_threads: 4         # Threads CPU (ajusta para o teu CPU)
  n_gpu_layers: 0      # 0 para CPU-only

reasoning:
  save_to_file: true   # Gravar raciocinio
  max_steps: 10        # Maximo de passos de raciocinio
```

## Resolucao de Problemas

### Erro: llama-cpp-python nao compila
```bash
sudo apt install build-essential cmake python3-dev
pip install llama-cpp-python --no-cache-dir --force-reinstall
```

### Erro: Modelo nao encontrado
```bash
mkdir -p ~/.local/share/guardian/models
cd ~/.local/share/guardian/models
wget https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf
```

### Erro: Memoria insuficiente
- Fecha outras aplicacoes
- Usa um modelo menor (TinyLlama ~700MB):
```bash
wget https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf
```
- Atualiza o `config.yaml` com o novo caminho

### Icone nao aparece no Desktop
```bash
# Re-criar o icone
cp ~/.local/share/applications/guardian.desktop ~/Desktop/
chmod +x ~/Desktop/guardian.desktop
gio set ~/Desktop/guardian.desktop metadata::trusted true
```

## Modelos Alternativos

| Modelo | Tamanho | RAM | Qualidade |
|--------|---------|-----|-----------|
| Mistral-7B Q4 | ~4.4GB | ~5GB | Excelente |
| Phi-2 Q4 | ~1.6GB | ~2GB | Boa |
| TinyLlama Q4 | ~700MB | ~1GB | Basica |

## Licenca

MIT License
