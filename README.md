# AI Terminal Desktop - GNOME Edition

A GTK4/Libadwaita desktop application for AI-powered terminal operations on Fedora.

## Features

- **Native GNOME Experience**: Built with GTK4 and Libadwaita for seamless integration with GNOME desktop
- **SSH Connection Management**: Connect to remote servers via SSH
- **AI-Powered Command Execution**: Use Ollama AI to interpret natural language requests and execute commands
- **Conversation History**: Track your interactions with the AI
- **Settings Persistence**: Save connection settings for quick access

## Installation on Fedora

### 1. Install System Dependencies

```bash
# Install GTK4 and Libadwaita
sudo dnf install gtk4 libadwaita

# Install Python development packages
sudo dnf install python3-devel python3-pip python3-gobject gtk4-devel

# Install additional dependencies
sudo dnf install gobject-introspection-devel cairo-devel cairo-gobject-devel
```

### 2. Install Python Dependencies

```bash
# Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install -r requirements.txt
```

### 3. Install Ollama (if not already installed)

```bash
# Download and install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model (e.g., llama2)
ollama pull llama2
```

## Running the Application

```bash
# Make sure you're in the AIDesktop directory
cd AIDesktop

# If using virtual environment, activate it
source venv/bin/activate

# Run the application
python3 main.py
```

Or make it executable and run directly:

```bash
chmod +x main.py
./main.py
```

## Usage

1. **Configure SSH Connection**:
   - Enter your SSH server details in the left sidebar
   - Click "Connect to SSH" to establish connection

2. **Configure Ollama**:
   - Set the Ollama URL (default: http://localhost:11434)
   - Select your AI model
   - Customize AI name and role
   - Click "Test Ollama Connection" to verify

3. **Start Chatting**:
   - Type natural language requests in the input field
   - The AI will interpret and execute commands on your SSH server
   - View command output and AI responses in the chat area

## Examples

- "Show me the current directory"
- "List all files in /var/log"
- "Check disk usage"
- "What processes are using the most memory?"
- "Create a new directory called test"

## Creating a Desktop Entry (Optional)

Create a `.desktop` file for easy launching:

```bash
# Create the desktop file
cat > ~/.local/share/applications/aiterminal-desktop.desktop <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=AI Terminal Desktop
Comment=AI-powered terminal with SSH and Ollama
Exec=/path/to/AIDesktop/main.py
Icon=utilities-terminal
Terminal=false
Categories=System;Utility;
EOF

# Make it executable
chmod +x ~/.local/share/applications/aiterminal-desktop.desktop
```

## Troubleshooting

### GTK4 Import Error

If you get an error about GTK4 not being found:

```bash
# Make sure PyGObject is installed system-wide
sudo dnf install python3-gobject

# Or reinstall in your virtual environment
pip install --force-reinstall PyGObject
```

### Libadwaita Not Found

```bash
# Install libadwaita development files
sudo dnf install libadwaita-devel
```

### SSH Connection Issues

- Verify the SSH server is accessible
- Check firewall settings
- Ensure correct credentials are provided

### Ollama Connection Issues

- Verify Ollama is running: `systemctl status ollama`
- Start Ollama if needed: `ollama serve`
- Check the Ollama URL is correct

## Configuration

Settings are stored in: `~/.config/aiterminal-desktop/settings.json`

## Architecture

- **main.py**: Main application window and GTK UI
- **ssh_client.py**: SSH connection management
- **ollama_client.py**: Ollama AI integration
- **settings_manager.py**: Settings persistence

## Requirements

- Fedora 35+ (or any Linux with GNOME 42+)
- Python 3.9+
- GTK4
- Libadwaita 1.0+
- Ollama running locally or remotely

## License

MIT License - Same as the original AI Terminal project
