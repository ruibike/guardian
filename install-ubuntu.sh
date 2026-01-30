#!/bin/bash
#
# Guardian - Instalador para Ubuntu
# Instala tudo automaticamente e cria icone no desktop
#

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║         GUARDIAN - Instalador Ubuntu                      ║"
echo "║         Agente LLM Offline com Mistral-7B                 ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Diretorio de instalacao
INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_DIR="$HOME/.local/share/guardian/models"
VENV_DIR="$INSTALL_DIR/venv"

echo -e "${YELLOW}[1/6] Instalando dependencias do sistema...${NC}"
sudo apt update
sudo apt install -y python3 python3-pip python3-venv python3-dev \
    build-essential cmake git wget curl \
    python3-tk tk-dev

echo -e "${GREEN}[OK] Dependencias do sistema instaladas${NC}"

echo -e "${YELLOW}[2/6] Criando ambiente virtual Python...${NC}"
if [ -d "$VENV_DIR" ]; then
    echo "Ambiente virtual ja existe, removendo..."
    rm -rf "$VENV_DIR"
fi
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip wheel setuptools

echo -e "${GREEN}[OK] Ambiente virtual criado${NC}"

echo -e "${YELLOW}[3/6] Instalando llama-cpp-python (pode demorar)...${NC}"
# Instalar llama-cpp-python com suporte CPU otimizado
CMAKE_ARGS="-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS" \
    pip install llama-cpp-python --no-cache-dir --force-reinstall

echo -e "${GREEN}[OK] llama-cpp-python instalado${NC}"

echo -e "${YELLOW}[4/6] Instalando outras dependencias Python...${NC}"
pip install customtkinter>=5.2.0 Pillow>=9.0.0
pip install duckduckgo-search>=4.0 requests beautifulsoup4
pip install pyyaml rich psutil watchdog

echo -e "${GREEN}[OK] Dependencias Python instaladas${NC}"

echo -e "${YELLOW}[5/6] Descarregando modelo Mistral-7B (~4.4GB)...${NC}"
mkdir -p "$MODEL_DIR"
MODEL_FILE="$MODEL_DIR/mistral-7b-instruct-v0.2.Q4_K_M.gguf"

if [ -f "$MODEL_FILE" ]; then
    echo -e "${GREEN}Modelo ja existe em $MODEL_FILE${NC}"
else
    echo "Isto pode demorar dependendo da tua conexao..."
    wget -c --progress=bar:force:noscroll \
        "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf" \
        -O "$MODEL_FILE"
    echo -e "${GREEN}[OK] Modelo descarregado${NC}"
fi

# Atualizar config.yaml com o caminho do modelo
echo -e "${YELLOW}Atualizando configuracao...${NC}"
cat > "$INSTALL_DIR/config.yaml" << EOF
# Guardian Configuration
# Otimizado para 8GB RAM

llm:
  model_path: "$MODEL_FILE"
  n_ctx: 2048
  n_batch: 256
  n_threads: 4
  n_gpu_layers: 0
  max_tokens: 512
  temperature: 0.7
  top_p: 0.9

reasoning:
  save_to_file: true
  log_dir: "data/reasoning"
  max_steps: 10

firewall:
  enabled: true
  blocked_ips_file: "data/blocked_ips/blocked.txt"
  auto_block_suspicious: true

tools:
  file_search:
    max_results: 20
    exclude_dirs: [".git", "node_modules", "__pycache__", "venv"]
  web_search:
    max_results: 10
    safe_search: true
EOF

echo -e "${GREEN}[OK] Configuracao atualizada${NC}"

echo -e "${YELLOW}[6/6] Criando icone no Desktop...${NC}"

# Criar script de lancamento
cat > "$INSTALL_DIR/guardian-launch.sh" << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
source venv/bin/activate
python main.py "$@"
EOF
chmod +x "$INSTALL_DIR/guardian-launch.sh"

# Criar icone SVG
mkdir -p "$INSTALL_DIR/assets"
cat > "$INSTALL_DIR/assets/guardian-icon.svg" << 'EOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <defs>
    <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#1a5fb4"/>
      <stop offset="100%" style="stop-color:#3584e4"/>
    </linearGradient>
  </defs>
  <circle cx="50" cy="50" r="45" fill="url(#grad)"/>
  <path d="M50 20 L75 35 L75 55 C75 70 62 82 50 85 C38 82 25 70 25 55 L25 35 Z"
        fill="none" stroke="white" stroke-width="4"/>
  <circle cx="50" cy="50" r="12" fill="white"/>
  <circle cx="50" cy="50" r="6" fill="#1a5fb4"/>
</svg>
EOF

# Converter SVG para PNG (se possivel)
if command -v convert &> /dev/null; then
    convert -background none "$INSTALL_DIR/assets/guardian-icon.svg" \
        -resize 128x128 "$INSTALL_DIR/assets/guardian-icon.png" 2>/dev/null || true
fi

# Criar ficheiro .desktop
DESKTOP_FILE="$HOME/.local/share/applications/guardian.desktop"
mkdir -p "$HOME/.local/share/applications"

cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Guardian AI
GenericName=LLM Agent
Comment=Agente LLM Offline para seguranca Linux
Exec=$INSTALL_DIR/guardian-launch.sh
Icon=$INSTALL_DIR/assets/guardian-icon.svg
Terminal=false
Categories=Utility;Security;
Keywords=ai;llm;security;firewall;
StartupNotify=true
EOF

chmod +x "$DESKTOP_FILE"

# Copiar para o Desktop tambem
if [ -d "$HOME/Desktop" ]; then
    cp "$DESKTOP_FILE" "$HOME/Desktop/guardian.desktop"
    chmod +x "$HOME/Desktop/guardian.desktop"
    # Permitir execucao no GNOME
    gio set "$HOME/Desktop/guardian.desktop" metadata::trusted true 2>/dev/null || true
fi

if [ -d "$HOME/Ambiente de trabalho" ]; then
    cp "$DESKTOP_FILE" "$HOME/Ambiente de trabalho/guardian.desktop"
    chmod +x "$HOME/Ambiente de trabalho/guardian.desktop"
    gio set "$HOME/Ambiente de trabalho/guardian.desktop" metadata::trusted true 2>/dev/null || true
fi

# Atualizar cache de aplicacoes
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

echo -e "${GREEN}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║              INSTALACAO COMPLETA!                         ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo -e "O Guardian foi instalado com sucesso!"
echo ""
echo -e "${BLUE}Para executar:${NC}"
echo "  1. Clica no icone 'Guardian AI' no desktop/menu"
echo "  2. Ou no terminal: $INSTALL_DIR/guardian-launch.sh"
echo "  3. Ou: cd $INSTALL_DIR && source venv/bin/activate && python main.py"
echo ""
echo -e "${BLUE}Modelo LLM:${NC} $MODEL_FILE"
echo -e "${BLUE}RAM necessaria:${NC} ~4-5GB para o modelo + sistema"
echo ""
echo -e "${YELLOW}Primeira execucao pode demorar a carregar o modelo.${NC}"
echo ""
