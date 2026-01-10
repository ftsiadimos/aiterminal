#!/bin/bash

# Installation script for AI Terminal Desktop on Fedora

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VERSION=$(cat "$SCRIPT_DIR/../VERSION" 2>/dev/null || echo "1.0.0")

echo "===================================="
echo "AI Terminal Desktop Installation"
echo "===================================="
echo ""

# Check if running on Fedora
if [ ! -f /etc/fedora-release ]; then
    echo "Warning: This script is designed for Fedora. Continuing anyway..."
fi

# Install system dependencies
echo "Installing system dependencies..."
sudo dnf install -y \
    gtk4 \
    libadwaita \
    python3-devel \
    python3-pip \
    python3-gobject \
    gtk4-devel \
    gobject-introspection-devel \
    cairo-devel \
    cairo-gobject-devel \
    python3-cairo \
    python3-paramiko \
    python3-requests

if [ $? -ne 0 ]; then
    echo "Error: Failed to install system dependencies"
    exit 1
fi

# Install additional Python packages user-level (not in venv)
echo ""
echo "Installing additional Python dependencies..."
pip3 install --user paramiko requests

if [ $? -ne 0 ]; then
    echo "Warning: Failed to install some Python dependencies, but continuing..."
fi

# Check if Ollama is installed
echo ""
echo "Checking for Ollama..."
if ! command -v ollama &> /dev/null; then
    echo "Ollama not found. Would you like to install it? (y/n)"
    read -r install_ollama
    if [ "$install_ollama" = "y" ] || [ "$install_ollama" = "Y" ]; then
        echo "Installing Ollama..."
        curl -fsSL https://ollama.com/install.sh | sh
        
        echo "Pulling llama2 model..."
        ollama pull llama2
    fi
else
    echo "Ollama is already installed"
fi

# Make main.py executable
chmod +x main.py

# Create desktop entry
echo ""
echo "Would you like to create a desktop entry? (y/n)"
read -r create_desktop

if [ "$create_desktop" = "y" ] || [ "$create_desktop" = "Y" ]; then
    DESKTOP_FILE="$HOME/.local/share/applications/aiterminal-desktop.desktop"
    CURRENT_DIR="$(pwd)"
    
    mkdir -p "$HOME/.local/share/applications"
    
    # Install the application icon for the desktop entry
    ICON_SRC="$SCRIPT_DIR/logoaitermin.png"
    if [ -f "$ICON_SRC" ]; then
        echo "Installing application icon..."
        mkdir -p "$HOME/.local/share/icons/hicolor/scalable/apps"
        cp "$ICON_SRC" "$HOME/.local/share/icons/hicolor/scalable/apps/aiterminal-desktop.png"
        echo "Icon installed to: $HOME/.local/share/icons/hicolor/scalable/apps/aiterminal-desktop.png"
        # If xdg-icon-resource is available, register the icon (user-level)
        if command -v xdg-icon-resource &> /dev/null; then
            xdg-icon-resource install --context apps --size scalable "$ICON_SRC" aiterminal-desktop || true
            echo "Registered icon with xdg-icon-resource"
        fi
    else
        echo "Icon source not found: $ICON_SRC (skipping icon install)"
    fi

    cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Version=$VERSION
Type=Application
Name=AI Terminal Desktop
Comment=AI-powered terminal with SSH and Ollama
Exec=python3 $CURRENT_DIR/main.py
Icon=aiterminal-desktop
Terminal=false
Categories=System;Utility;
EOF

    chmod +x "$DESKTOP_FILE"
    echo "Desktop entry created at $DESKTOP_FILE"
fi

echo ""
echo "===================================="
echo "Installation complete!"
echo "===================================="
echo ""
echo "To run the application:"
echo "  python3 main.py"
echo ""
echo "Or if you created a desktop entry, search for 'AI Terminal Desktop' in your applications menu"
echo ""
