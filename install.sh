#!/bin/bash
# Guardian - Script de Instalação para Ubuntu
# Otimizado para sistemas com 8GB de RAM

set -e

echo "=========================================="
echo "  Guardian - Instalação"
echo "  Agente LLM Offline para Ubuntu"
echo "=========================================="
echo

# Check if running on Ubuntu/Debian
if ! command -v apt &> /dev/null; then
    echo "[ERRO] Este script requer apt (Ubuntu/Debian)"
    exit 1
fi

# Update package list
echo "[1/5] A atualizar lista de pacotes..."
sudo apt update

# Install system dependencies
echo "[2/5] A instalar dependências do sistema..."
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-gi \
    python3-gi-cairo \
    gir1.2-gtk-4.0 \
    libadwaita-1-dev \
    gir1.2-adw-1

# Create virtual environment
echo "[3/5] A criar ambiente virtual..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate and install Python dependencies
echo "[4/5] A instalar dependências Python..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create data directories
echo "[5/5] A criar diretórios de dados..."
mkdir -p data/reasoning
mkdir -p data/blocked_ips
mkdir -p logs
mkdir -p ~/.local/share/guardian/models

# Initialize blocked IPs file
if [ ! -f "data/blocked_ips/blocked.txt" ]; then
    echo "{}" > data/blocked_ips/blocked.txt
fi

echo
echo "=========================================="
echo "  Instalação Concluída!"
echo "=========================================="
echo
echo "Para executar o Guardian:"
echo "  source venv/bin/activate"
echo "  python main.py          # Interface gráfica"
echo "  python main.py --cli    # Modo terminal"
echo
echo "Para instalar um modelo LLM (opcional):"
echo "  cd ~/.local/share/guardian/models"
echo "  wget https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
echo
echo "Ou para sistemas com menos RAM:"
echo "  wget https://huggingface.co/TheBloke/phi-2-GGUF/resolve/main/phi-2.Q4_K_M.gguf"
echo
