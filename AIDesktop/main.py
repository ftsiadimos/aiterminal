#!/usr/bin/env python3
"""
AI Terminal Desktop Application for GNOME
GTK-based desktop version of the AI Terminal
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gio, Pango
import json
import os
import threading
import datetime
from ssh_client import SSHClient
from local_client import LocalClient
from ollama_client import OllamaClient
from settings_manager import SettingsManager

# Ensure the application's directory and the project root are on sys.path so
# top-level modules like `config` can be imported when running from the
# `AIDesktop` directory or after installing the package into /opt
import sys
_app_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.abspath(os.path.join(_app_dir, '..'))
for _p in (_app_dir, _project_root):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import config

# Maximum number of characters to display from command output by default
MAX_OUTPUT_CHARS = 150000

class AITerminalWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.set_default_size(1200, 800)
        self.set_title("AI Terminal Desktop")
        
        # Initialize components
        self.ssh_client = None
        self.local_mode = True  # Start in local mode by default
        self.ollama_client = None
        self.settings_manager = SettingsManager()
        self.conversation_history = []
        self.saved_settings = {}
        self.ssh_servers = []  # List of saved SSH server configurations
        
        # Initialize entry references (will be created in settings dialog)
        self.ssh_server_selector = None  # Dropdown for saved servers
        self.ssh_server_name_entry = None
        self.ssh_host_entry = None
        self.ssh_port_entry = None
        self.ssh_username_entry = None
        self.ssh_password_entry = None
        self.ollama_host_entry = None
        self.model_selector = None
        self.ai_name_entry = None
        self.ai_role_entry = None
        
        # Build UI
        self.build_ui()
        
        # Load saved settings
        self.load_settings()
        
        # Initialize local terminal client
        self.ssh_client = LocalClient()
        self.ssh_client.connect()
        self.ssh_status_label.set_label("Terminal: ✓ Local")
        
        # Welcome message
        self.append_chat_message("SYSTEM", "Welcome to AI Terminal Desktop! Running in local terminal mode.", "system")
        
        # Auto-connect to Ollama after a short delay
        GLib.timeout_add(500, self.auto_connect_ollama)
    
    def build_ui(self):
        """Build the main UI"""
        # Add CSS for terminal-style dark theme
        css_provider = Gtk.CssProvider()
        css_provider.load_from_string("""
            window {
                background-color: #000000;
            }
            
            .toolbar {
                background-color: #1a1a1a;
                border-top: 1px solid #333333;
            }
            
            textview {
                background-color: #000000;
                color: #00ff00;
                font-family: 'Monospace', 'Courier New', monospace;
                font-size: 13pt;
                padding: 15px;
            }
            
            textview text {
                background-color: #000000;
                color: #00ff00;
                caret-color: #00ff00;
            }
            
            entry {
                background-color: #0a0a0a;
                color: #00ff00;
                border: 1px solid #333333;
                border-radius: 2px;
                padding: 10px;
                font-family: 'Monospace', monospace;
                caret-color: #00ff00;
            }
            
            entry:focus {
                border-color: #00ff00;
                box-shadow: 0 0 5px rgba(0, 255, 0, 0.3);
            }
            
            button {
                background-color: #1a1a1a;
                color: #00ff00;
                border: 1px solid #333333;
                border-radius: 2px;
                padding: 8px 16px;
                font-family: monospace;
            }
            
            button:hover {
                background-color: #2a2a2a;
                border-color: #00ff00;
            }
            
            button.suggested-action {
                background-color: #003300;
                border-color: #00ff00;
            }
            
            button.suggested-action:hover {
                background-color: #005500;
            }
            
            .dim-label {
                color: #00aa00;
            }
            
            headerbar {
                background-color: #0a0a0a;
                color: #00ff00;
                border-bottom: 1px solid #333333;
            }
            
            separator {
                background-color: #333333;
            }
            
            label {
                color: #00ff00;
            }
            
            .title-2 {
                color: #00ff00;
                font-size: 16pt;
                font-weight: bold;
            }
            
            /* Preferences window styling */
            preferenceswindow {
                background-color: #0a0a0a;
            }
            
            preferencespage {
                background-color: #0a0a0a;
            }
            
            preferencesgroup {
                background-color: #0a0a0a;
            }
            
            preferencesgroup > box {
                background-color: #1a1a1a;
                border: 1px solid #00ff00;
                border-radius: 0px;
                padding: 8px;
            }
            
            row {
                background-color: #1a1a1a;
                color: #00ff00;
                border-radius: 0px;
                padding: 4px;
            }
            
            row:hover {
                background-color: #2a2a2a;
            }
            
            row entry {
                background-color: #000000;
                color: #00ff00;
                border: 1px solid #00ff00;
                border-radius: 0px;
                padding: 8px;
                font-family: monospace;
            }
            
            row entry:focus {
                background-color: #0a0a0a;
                border-color: #00ff00;
                box-shadow: 0 0 3px rgba(0, 255, 0, 0.5);
            }
            
            combobox {
                background-color: #000000;
                color: #00ff00;
                border: 1px solid #00ff00;
                border-radius: 0px;
            }
            
            combobox button {
                background-color: #1a1a1a;
                border-radius: 0px;
            }
            
            .title {
                color: #00ff00;
                font-weight: bold;
            }
            
            .subtitle {
                color: #00aa00;
            }
            
            preferencesgroup > label {
                color: #00ff00;
                font-weight: bold;
            }
        """)
        
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        
        # Main box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_content(main_box)
        
        # Header bar
        header = Adw.HeaderBar()
        main_box.append(header)
        
        # Title
        header.set_title_widget(Gtk.Label(label="AI Terminal Desktop"))
        
        # Settings button
        settings_button = Gtk.Button()
        settings_button.set_icon_name("preferences-system-symbolic")
        settings_button.connect("clicked", self.on_show_settings)
        header.pack_end(settings_button)
        
        # Menu button
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        header.pack_end(menu_button)
        
        # Menu
        menu = Gio.Menu()
        menu.append("About", "app.about")
        menu.append("Quit", "app.quit")
        menu_button.set_menu_model(menu)
        
        # Status bar under header
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        status_box.set_margin_start(12)
        status_box.set_margin_end(12)
        status_box.set_margin_top(6)
        status_box.set_margin_bottom(6)
        status_box.add_css_class("toolbar")
        
        self.ssh_status_label = Gtk.Label(label="SSH: Not Connected")
        self.ssh_status_label.add_css_class("dim-label")
        status_box.append(self.ssh_status_label)
        
        status_box.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
        
        self.ollama_status_label = Gtk.Label(label="AI: Not Connected")
        self.ollama_status_label.add_css_class("dim-label")
        status_box.append(self.ollama_status_label)
        
        status_box.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
        
        # Quick server selector
        server_label = Gtk.Label(label="Server:")
        server_label.add_css_class("dim-label")
        status_box.append(server_label)
        
        self.quick_server_selector = Gtk.ComboBoxText()
        self.quick_server_selector.append_text("Local")  # Local mode first
        self.quick_server_selector.set_active(0)
        self.quick_server_selector.connect("changed", self.on_quick_server_connect)
        status_box.append(self.quick_server_selector)
        
        main_box.append(status_box)
        main_box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        
        # Main content - chat interface
        self.main_content = self.create_main_content()
        main_box.append(self.main_content)
    
    def on_show_settings(self, button):
        """Show settings dialog"""
        dialog = Adw.PreferencesWindow(transient_for=self)
        dialog.set_title("Settings")
        
        # SSH Settings Page
        ssh_page = Adw.PreferencesPage()
        ssh_page.set_title("SSH Connection")
        ssh_page.set_icon_name("network-server-symbolic")
        
        # Saved Servers Group
        saved_servers_group = Adw.PreferencesGroup()
        saved_servers_group.set_title("Saved Servers")
        
        # Server selector
        server_selector_row = Adw.ActionRow()
        server_selector_row.set_title("Select Server")
        server_selector_row.set_subtitle("Choose from saved SSH servers")
        
        self.ssh_server_selector = Gtk.ComboBoxText()
        self.ssh_server_selector.set_valign(Gtk.Align.CENTER)
        self.ssh_server_selector.append_text("<New Server>")
        self.ssh_server_selector.set_active(0)
        self.ssh_server_selector.connect("changed", self.on_server_selected)
        server_selector_row.add_suffix(self.ssh_server_selector)
        saved_servers_group.add(server_selector_row)
        
        ssh_page.add(saved_servers_group)
        
        # Current Server Configuration Group
        ssh_group = Adw.PreferencesGroup()
        ssh_group.set_title("Server Configuration")
        
        self.ssh_server_name_entry = Adw.EntryRow()
        self.ssh_server_name_entry.set_title("Server Name")
        self.ssh_server_name_entry.set_text("My Server")
        ssh_group.add(self.ssh_server_name_entry)
        
        self.ssh_host_entry = Adw.EntryRow()
        self.ssh_host_entry.set_title("Host")
        ssh_group.add(self.ssh_host_entry)
        
        self.ssh_port_entry = Adw.EntryRow()
        self.ssh_port_entry.set_title("Port")
        self.ssh_port_entry.set_text("22")
        ssh_group.add(self.ssh_port_entry)
        
        self.ssh_username_entry = Adw.EntryRow()
        self.ssh_username_entry.set_title("Username")
        ssh_group.add(self.ssh_username_entry)
        
        self.ssh_password_entry = Adw.PasswordEntryRow()
        self.ssh_password_entry.set_title("Password")
        ssh_group.add(self.ssh_password_entry)
        
        ssh_page.add(ssh_group)
        
        # SSH Actions
        ssh_action_group = Adw.PreferencesGroup()
        
        ssh_button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        ssh_button_box.set_halign(Gtk.Align.CENTER)
        ssh_button_box.set_margin_top(12)
        ssh_button_box.set_margin_bottom(12)
        
        save_server_btn = Gtk.Button(label="Save Server")
        save_server_btn.connect("clicked", self.on_save_server)
        ssh_button_box.append(save_server_btn)
        
        delete_server_btn = Gtk.Button(label="Delete Server")
        delete_server_btn.connect("clicked", self.on_delete_server)
        ssh_button_box.append(delete_server_btn)
        
        self.ssh_connect_btn = Gtk.Button(label="Connect")
        self.ssh_connect_btn.add_css_class("suggested-action")
        self.ssh_connect_btn.connect("clicked", self.on_ssh_connect)
        ssh_button_box.append(self.ssh_connect_btn)
        
        disconnect_btn = Gtk.Button(label="Disconnect")
        disconnect_btn.connect("clicked", self.on_ssh_disconnect)
        ssh_button_box.append(disconnect_btn)
        
        ssh_action_group.add(ssh_button_box)
        ssh_page.add(ssh_action_group)
        
        dialog.add(ssh_page)
        
        # AI Settings Page
        ai_page = Adw.PreferencesPage()
        ai_page.set_title("AI Settings")
        ai_page.set_icon_name("application-x-executable-symbolic")
        
        ollama_group = Adw.PreferencesGroup()
        ollama_group.set_title("Ollama Configuration")
        
        self.ollama_host_entry = Adw.EntryRow()
        self.ollama_host_entry.set_title("Ollama URL")
        self.ollama_host_entry.set_text("http://localhost:11434")
        ollama_group.add(self.ollama_host_entry)
        
        # Load Models button
        load_models_row = Adw.ActionRow()
        load_models_row.set_title("Available Models")
        load_models_row.set_subtitle("Click to load models from Ollama")
        
        load_models_btn = Gtk.Button(label="Load Models")
        load_models_btn.set_valign(Gtk.Align.CENTER)
        load_models_btn.connect("clicked", self.on_load_models)
        load_models_row.add_suffix(load_models_btn)
        ollama_group.add(load_models_row)
        
        # Model selector (ComboBoxText)
        model_row = Adw.ActionRow()
        model_row.set_title("Select Model")
        
        self.model_selector = Gtk.ComboBoxText()
        self.model_selector.set_valign(Gtk.Align.CENTER)
        self.model_selector.append_text("llama2")  # Default
        self.model_selector.set_active(0)
        model_row.add_suffix(self.model_selector)
        ollama_group.add(model_row)
        
        ai_page.add(ollama_group)
        
        # AI Personality
        ai_personality_group = Adw.PreferencesGroup()
        ai_personality_group.set_title("AI Personality")
        
        self.ai_name_entry = Adw.EntryRow()
        self.ai_name_entry.set_title("AI Name")
        self.ai_name_entry.set_text("Jarvis")
        ai_personality_group.add(self.ai_name_entry)
        
        self.ai_role_entry = Adw.EntryRow()
        self.ai_role_entry.set_title("AI Role")
        self.ai_role_entry.set_text("Linux Expert")
        ai_personality_group.add(self.ai_role_entry)
        
        # Max output characters setting (numeric entry)
        self.max_output_entry = Adw.EntryRow()
        self.max_output_entry.set_title("Max Output Characters")
        self.max_output_entry.set_text(str(MAX_OUTPUT_CHARS))
        ai_personality_group.add(self.max_output_entry)
        
        ai_page.add(ai_personality_group)
        
        # Ollama Actions
        ollama_action_group = Adw.PreferencesGroup()
        
        ollama_button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        ollama_button_box.set_halign(Gtk.Align.CENTER)
        ollama_button_box.set_margin_top(12)
        ollama_button_box.set_margin_bottom(12)
        
        self.ollama_connect_btn = Gtk.Button(label="Test Connection")
        self.ollama_connect_btn.add_css_class("suggested-action")
        self.ollama_connect_btn.connect("clicked", self.on_ollama_test)
        ollama_button_box.append(self.ollama_connect_btn)
        
        save_btn = Gtk.Button(label="Save Settings")
        save_btn.connect("clicked", lambda b: self.save_settings())
        ollama_button_box.append(save_btn)
        
        ollama_action_group.add(ollama_button_box)
        ai_page.add(ollama_action_group)
        
        dialog.add(ai_page)
        
        # Load current settings into dialog
        self.load_settings_to_dialog()
        
        dialog.set_modal(False)  # Make dialog non-modal so chat is visible
        dialog.present()
    
    def create_main_content(self):
        """Create the main content area with chat interface"""
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        
        # Chat display area with dark theme
        self.chat_view = Gtk.TextView()
        self.chat_view.set_editable(False)
        self.chat_view.set_cursor_visible(False)
        self.chat_view.set_focusable(False)
        self.chat_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.chat_view.set_margin_start(16)
        self.chat_view.set_margin_end(16)
        self.chat_view.set_margin_top(16)
        self.chat_view.set_margin_bottom(16)
        self.chat_view.add_css_class("monospace")
        
        # Text buffer
        self.chat_buffer = self.chat_view.get_buffer()
        
        # Create text tags for formatting - terminal-style colors
        self.chat_buffer.create_tag("user", weight=Pango.Weight.BOLD, foreground="#00ffff")  # Cyan
        self.chat_buffer.create_tag("ai", weight=Pango.Weight.BOLD, foreground="#00ff00")  # Green
        self.chat_buffer.create_tag("system", foreground="#ffff00", style=Pango.Style.ITALIC)  # Yellow
        self.chat_buffer.create_tag("command", family="monospace", foreground="#ff00ff", weight=Pango.Weight.BOLD)  # Magenta
        self.chat_buffer.create_tag("output", family="monospace", foreground="#aaaaaa")  # Gray
        self.chat_buffer.create_tag("prompt", foreground="#00ff00")  # Green
        
        # Scrolled window for chat
        chat_scroll = Gtk.ScrolledWindow()
        chat_scroll.set_child(self.chat_view)
        chat_scroll.set_vexpand(True)
        content_box.append(chat_scroll)
        
        # Input area at bottom
        input_frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        input_frame.add_css_class("toolbar")
        
        input_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        input_box.set_margin_start(16)
        input_box.set_margin_end(16)
        input_box.set_margin_top(12)
        input_box.set_margin_bottom(12)
        
        # Terminal prompt symbol
        prompt_label = Gtk.Label(label="$")
        prompt_label.add_css_class("title-2")
        input_box.append(prompt_label)
        
        # Input entry
        self.input_entry = Gtk.Entry()
        self.input_entry.set_placeholder_text("Enter command or natural language request...")
        self.input_entry.set_hexpand(True)
        self.input_entry.connect("activate", self.on_send_message)
        
        # Add key press event for tab completion
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self.on_key_pressed)
        self.input_entry.add_controller(key_controller)
        
        input_box.append(self.input_entry)
        
        # Completion state
        self.completions = []
        self.completion_index = 0
        self.last_completion_text = ""
        
        # Send button
        self.send_btn = Gtk.Button(label="Send")
        self.send_btn.add_css_class("suggested-action")
        self.send_btn.connect("clicked", self.on_send_message)
        input_box.append(self.send_btn)
        
        # Clear button
        clear_btn = Gtk.Button(label="Clear")
        clear_btn.connect("clicked", self.on_clear_chat)
        input_box.append(clear_btn)
        
        input_frame.append(input_box)
        content_box.append(input_frame)
        
        # Add window-level key controller for navigation shortcuts
        window_key_controller = Gtk.EventControllerKey()
        window_key_controller.connect("key-pressed", self.on_window_key_pressed)
        self.add_controller(window_key_controller)
        
        return content_box
    
    def append_chat_message(self, role, message, tag=None):
        """Append a message to the chat display - terminal style"""
        # Check if chat_buffer exists (UI might not be fully initialized yet)
        if not hasattr(self, 'chat_buffer') or self.chat_buffer is None:
            return
        
        # Add timestamp
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        end_iter = self.chat_buffer.get_end_iter()
        self.chat_buffer.insert(end_iter, f"[{timestamp}] ")
        
        # Insert role with tag if provided
        if tag:
            end_iter = self.chat_buffer.get_end_iter()
            self.chat_buffer.insert_with_tags_by_name(end_iter, f"{role}", tag)
            end_iter = self.chat_buffer.get_end_iter()
            self.chat_buffer.insert(end_iter, f": {message}\n")
        else:
            end_iter = self.chat_buffer.get_end_iter()
            self.chat_buffer.insert(end_iter, f"{role}: {message}\n")
        
        # Add empty line for readability
        end_iter = self.chat_buffer.get_end_iter()
        self.chat_buffer.insert(end_iter, "\n")
        
        # Auto-scroll to bottom
        end_iter = self.chat_buffer.get_end_iter()
        mark = self.chat_buffer.create_mark(None, end_iter, False)
        self.chat_view.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)
    
    def scroll_to_top(self):
        """Scroll the chat view to the top"""
        if hasattr(self, 'chat_view') and self.chat_view is not None:
            start_iter = self.chat_buffer.get_start_iter()
            self.chat_view.scroll_to_iter(start_iter, 0.0, True, 0.0, 0.0)
        return False  # Remove from idle queue
    
    def scroll_to_bottom(self):
        """Scroll the chat view to the bottom"""
        if hasattr(self, 'chat_view') and self.chat_view is not None:
            end_iter = self.chat_buffer.get_end_iter()
            mark = self.chat_buffer.create_mark(None, end_iter, False)
            self.chat_view.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)
        return False  # Remove from idle queue
    
    def on_window_key_pressed(self, controller, keyval, keycode, state):
        """Handle window-level key press events for navigation"""
        from gi.repository import Gdk
        
        # Check if Home key was pressed - scroll to top
        if keyval == Gdk.KEY_Home:
            self.scroll_to_top()
            return True  # Stop event propagation
        # Check if End key was pressed - scroll to bottom
        elif keyval == Gdk.KEY_End:
            self.scroll_to_bottom()
            return True  # Stop event propagation
        
        return False
    
    def on_key_pressed(self, controller, keyval, keycode, state):
        """Handle key press events for tab completion"""
        from gi.repository import Gdk
        
        # Check if Tab key was pressed
        if keyval == Gdk.KEY_Tab:
            self.handle_tab_completion()
            return True  # Stop event propagation
        else:
            # Reset completion state on any other key
            self.completions = []
            self.completion_index = 0
            self.last_completion_text = ""
        
        return False
    
    def handle_tab_completion(self):
        """Handle tab completion"""
        if not self.ssh_client or not self.ssh_client.connected:
            return
        
        current_text = self.input_entry.get_text()
        cursor_pos = self.input_entry.get_position()
        
        # Get the word to complete (text before cursor)
        text_before_cursor = current_text[:cursor_pos]
        
        # Find the start of the current word
        words = text_before_cursor.split()
        if not words:
            return
        
        partial_word = words[-1] if words else ""
        
        # If this is a new completion request or different text
        if current_text != self.last_completion_text or not self.completions:
            # Get completions from SSH
            def get_completions_thread():
                completions = self.ssh_client.get_completions(partial_word)
                GLib.idle_add(self.apply_completions, completions, current_text, partial_word)
            
            thread = threading.Thread(target=get_completions_thread, daemon=True)
            thread.start()
        else:
            # Cycle through existing completions
            if self.completions:
                self.completion_index = (self.completion_index + 1) % len(self.completions)
                self.apply_completion(self.completions[self.completion_index], current_text, partial_word)
    
    def apply_completions(self, completions, original_text, partial_word):
        """Apply completions received from SSH"""
        self.completions = completions
        self.completion_index = 0
        self.last_completion_text = original_text
        
        if completions:
            if len(completions) == 1:
                # Single completion - apply it
                self.apply_completion(completions[0], original_text, partial_word)
            else:
                # Multiple completions - show first one and indicate there are more
                self.apply_completion(completions[0], original_text, partial_word)
                self.append_chat_message("SYSTEM", f"{len(completions)} completions available. Press Tab again to cycle.", "system")
        
        return False
    
    def apply_completion(self, completion, original_text, partial_word):
        """Apply a single completion to the input"""
        cursor_pos = self.input_entry.get_position()
        text_before = original_text[:cursor_pos]
        text_after = original_text[cursor_pos:]
        
        # Replace the partial word with the completion
        if partial_word:
            # Remove partial word from end
            prefix = text_before[:-len(partial_word)]
            new_text = prefix + completion + text_after
        else:
            new_text = text_before + completion + text_after
        
        self.input_entry.set_text(new_text)
        # Set cursor position after the completion
        new_pos = len(prefix) + len(completion) if partial_word else cursor_pos + len(completion)
        self.input_entry.set_position(new_pos)
    
    def on_server_selected(self, combo):
        """Handle server selection from dropdown"""
        server_name = combo.get_active_text()
        if not server_name or server_name == "<New Server>":
            # Clear fields for new server
            self.ssh_server_name_entry.set_text("My Server")
            self.ssh_host_entry.set_text("")
            self.ssh_port_entry.set_text("22")
            self.ssh_username_entry.set_text("")
            self.ssh_password_entry.set_text("")
            return
        
        # Load server configuration
        for server in self.ssh_servers:
            if server.get('name') == server_name:
                self.ssh_server_name_entry.set_text(server.get('name', ''))
                self.ssh_host_entry.set_text(server.get('host', ''))
                self.ssh_port_entry.set_text(str(server.get('port', 22)))
                self.ssh_username_entry.set_text(server.get('username', ''))
                self.ssh_password_entry.set_text(server.get('password', ''))
                break
    
    def on_save_server(self, button):
        """Save current server configuration"""
        server_name = self.ssh_server_name_entry.get_text().strip()
        host = self.ssh_host_entry.get_text().strip()
        
        if not server_name or not host:
            self.show_error_dialog("Server name and host are required")
            return
        
        # Create server config
        server_config = {
            'name': server_name,
            'host': host,
            'port': int(self.ssh_port_entry.get_text() or 22),
            'username': self.ssh_username_entry.get_text(),
            'password': self.ssh_password_entry.get_text()
        }
        
        # Check if server already exists
        existing_index = -1
        for i, server in enumerate(self.ssh_servers):
            if server.get('name') == server_name:
                existing_index = i
                break
        
        if existing_index >= 0:
            # Update existing server
            self.ssh_servers[existing_index] = server_config
        else:
            # Add new server
            self.ssh_servers.append(server_config)
        
        # Save to settings
        self.save_settings()
        
        # Update dropdown
        self.refresh_server_dropdown()
        
        # Select the saved server
        for i in range(self.ssh_server_selector.get_model().__len__()):
            self.ssh_server_selector.set_active(i)
            if self.ssh_server_selector.get_active_text() == server_name:
                break
        
        self.append_chat_message("SYSTEM", f"Server '{server_name}' saved successfully", "system")
    
    def on_delete_server(self, button):
        """Delete selected server configuration"""
        server_name = self.ssh_server_selector.get_active_text()
        
        if not server_name or server_name == "<New Server>":
            self.show_error_dialog("Please select a server to delete")
            return
        
        # Remove from list
        self.ssh_servers = [s for s in self.ssh_servers if s.get('name') != server_name]
        
        # Save settings
        self.save_settings()
        
        # Refresh dropdown and select new server
        self.refresh_server_dropdown()
        self.ssh_server_selector.set_active(0)
        
        self.append_chat_message("SYSTEM", f"Server '{server_name}' deleted", "system")
    
    def refresh_server_dropdown(self):
        """Refresh the server dropdown list"""
        # Update settings dialog dropdown
        if self.ssh_server_selector:
            # Clear current items
            self.ssh_server_selector.remove_all()
            
            # Add new server option
            self.ssh_server_selector.append_text("<New Server>")
            
            # Add all saved servers
            for server in self.ssh_servers:
                self.ssh_server_selector.append_text(server.get('name', ''))
        
        # Update quick selector on main screen
        if hasattr(self, 'quick_server_selector'):
            current_selection = self.quick_server_selector.get_active_text()
            
            # Clear and repopulate
            self.quick_server_selector.remove_all()
            self.quick_server_selector.append_text("Local")  # Always have Local option first
            
            for server in self.ssh_servers:
                self.quick_server_selector.append_text(server.get('name', ''))
            
            # Try to restore previous selection
            if current_selection:
                for i in range(self.quick_server_selector.get_model().__len__()):
                    self.quick_server_selector.set_active(i)
                    if self.quick_server_selector.get_active_text() == current_selection:
                        return
            
            # Default to Local (first item)
            self.quick_server_selector.set_active(0)
    
    def on_quick_server_connect(self, combo):
        """Handle quick server selection and connection from main screen"""
        server_name = combo.get_active_text()
        
        if not server_name:
            return
        
        # Check if Local mode is selected
        if server_name == "Local":
            # Switch to local mode
            self.local_mode = True
            if self.ssh_client and hasattr(self.ssh_client, 'disconnect'):
                self.ssh_client.disconnect()
            
            self.ssh_client = LocalClient()
            self.ssh_client.connect()
            self.ssh_status_label.set_label("Terminal: ✓ Local")
            self.append_chat_message("SYSTEM", "Switched to local terminal mode", "system")
            return
        
        # Find the server configuration for remote connections
        for server in self.ssh_servers:
            if server.get('name') == server_name:
                host = server.get('host', '')
                username = server.get('username', '')
                password = server.get('password', '')
                port = server.get('port', 22)
                
                if not host or not username:
                    self.append_chat_message("ERROR", f"Server '{server_name}' has incomplete configuration", "system")
                    combo.set_active(0)  # Reset to Local
                    return
                
                # Switch to SSH mode
                self.local_mode = False
                
                # Connect to SSH
                self.ssh_status_label.set_label(f"Connecting to {server_name}...")
                self.append_chat_message("SYSTEM", f"Connecting to {server_name}...", "system")
                
                def connect_thread():
                    self.ssh_client = SSHClient(host, username, password, port=port)
                    success, message = self.ssh_client.connect()
                    GLib.idle_add(self.on_quick_connect_complete, success, message, server_name)
                
                thread = threading.Thread(target=connect_thread, daemon=True)
                thread.start()
                
                # Save as last server
                self.saved_settings['last_server'] = server_name
                self.settings_manager.save_settings(self.saved_settings)
                return
        
        # Server not found, reset to Local
        combo.set_active(0)
    
    def on_quick_connect_complete(self, success, message, server_name):
        """Handle quick connect completion"""
        if success:
            self.ssh_status_label.set_label(f"SSH: ✓ {server_name}")
            self.append_chat_message("SYSTEM", f"Connected to {server_name}", "system")
        else:
            self.ssh_status_label.set_label("SSH: ✗ Failed")
            self.append_chat_message("ERROR", f"Connection to {server_name} failed: {message}", "system")
            # Reset dropdown
            self.quick_server_selector.set_active(0)
        return False
    
    def on_ssh_connect(self, button):
        """Handle SSH connection"""
        host = self.ssh_host_entry.get_text()
        port = int(self.ssh_port_entry.get_text() or "22")
        username = self.ssh_username_entry.get_text()
        password = self.ssh_password_entry.get_text()
        
        if not host or not username:
            self.show_error_dialog("Please provide host and username")
            return
        
        # Disable button during connection
        self.ssh_connect_btn.set_sensitive(False)
        self.ssh_status_label.set_label("Connecting...")
        
        def connect_thread():
            self.ssh_client = SSHClient(host, username, password, port=port)
            success, message = self.ssh_client.connect()
            
            GLib.idle_add(self.on_ssh_connect_complete, success, message)
        
        thread = threading.Thread(target=connect_thread, daemon=True)
        thread.start()
    
    def on_ssh_connect_complete(self, success, message):
        """Handle SSH connection completion"""
        self.ssh_connect_btn.set_sensitive(True)
        
        if success:
            self.ssh_status_label.set_label("SSH: ✓ Connected")
            self.append_chat_message("SYSTEM", f"SSH connection established", "system")
            self.save_settings()
        else:
            self.ssh_status_label.set_label("SSH: ✗ Failed")
            self.show_error_dialog(f"SSH Connection failed: {message}")
        
        return False
    
    def on_ssh_disconnect(self, button):
        """Disconnect from SSH"""
        if self.ssh_client:
            self.ssh_client.disconnect()
            self.ssh_client = None
        self.ssh_status_label.set_label("SSH: Not Connected")
        self.append_chat_message("SYSTEM", "SSH connection closed", "system")
    
    def on_ollama_test(self, button):
        """Test Ollama connection"""
        ollama_url = self.ollama_host_entry.get_text()
        
        self.ollama_connect_btn.set_sensitive(False)
        self.ollama_status_label.set_label("Testing...")
        
        def test_thread():
            client = OllamaClient(host=ollama_url)
            success, message = client.test_connection()
            
            GLib.idle_add(self.on_ollama_test_complete, success, message)
        
        thread = threading.Thread(target=test_thread, daemon=True)
        thread.start()
    
    def on_ollama_test_complete(self, success, message):
        """Handle Ollama test completion"""
        self.ollama_connect_btn.set_sensitive(True)
        
        if success:
            self.ollama_status_label.set_label("AI: ✓ Ready")
            self.append_chat_message("SYSTEM", "Ollama AI connection successful", "system")
            self.save_settings()
        else:
            self.ollama_status_label.set_label("AI: ✗ Failed")
            self.show_error_dialog(f"Ollama connection failed: {message}")
        
        return False
    
    def on_load_models(self, button):
        """Load available models from Ollama"""
        ollama_url = self.ollama_host_entry.get_text()
        
        button.set_sensitive(False)
        button.set_label("Loading...")
        
        def load_thread():
            client = OllamaClient(host=ollama_url)
            success, models = client.list_models()
            
            GLib.idle_add(self.on_models_loaded, success, models, button)
        
        thread = threading.Thread(target=load_thread, daemon=True)
        thread.start()
    
    def on_models_loaded(self, success, models, button):
        """Handle models loaded from Ollama"""
        button.set_sensitive(True)
        button.set_label("Load Models")
        
        if success and models:
            # Clear existing models
            self.model_selector.remove_all()
            
            # Get current selected model
            current_model = self.saved_settings.get('ollama_model', 'llama2')
            active_index = 0
            
            # Add all models
            for i, model in enumerate(models):
                model_name = model.get('name', model) if isinstance(model, dict) else model
                self.model_selector.append_text(model_name)
                if model_name == current_model:
                    active_index = i
            
            # Set active model
            self.model_selector.set_active(active_index)
            
            self.append_chat_message("SYSTEM", f"Loaded {len(models)} models from Ollama", "system")
        else:
            error_msg = models if isinstance(models, str) else "Failed to load models"
            self.show_error_dialog(f"Could not load models: {error_msg}")
        
        return False
    
    def on_send_message(self, widget):
        """Handle sending a message"""
        message = self.input_entry.get_text().strip()
        if not message:
            return
        
        if not self.ssh_client or not self.ssh_client.connected:
            self.append_chat_message("ERROR", "Terminal not ready. Please wait or restart the application.", "system")
            return
        
        # Clear input
        self.input_entry.set_text("")
        
        # Add user message to chat
        self.append_chat_message("USER", message, "user")
        
        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": message})
        
        # Disable send button during processing
        self.send_btn.set_sensitive(False)
        self.input_entry.set_sensitive(False)
        
        # Process in background thread
        def process_thread():
            self.process_ai_command(message)
        
        thread = threading.Thread(target=process_thread, daemon=True)
        thread.start()
    
    def process_ai_command(self, request_text):
        """Process AI command and execute if needed"""
        try:
            # Get settings (use saved values or defaults)
            ollama_url = self.saved_settings.get('ollama_url', 'http://localhost:11434')
            model = self.saved_settings.get('ollama_model', 'llama2')
            ai_name = self.saved_settings.get('ai_name', 'Jarvis')
            ai_role = self.saved_settings.get('ai_role', 'Linux Expert')
            
            # Build context from history
            context = ""
            if self.conversation_history:
                context = "\n\nPrevious conversation context:\n"
                for msg in self.conversation_history[-5:]:
                    role = msg.get('role', 'user')
                    content = msg.get('content', '')
                    context += f"{role}: {content}\n"
            
            # Create prompt for AI
            prompt = f"""You are {ai_name}, a {ai_role}. YOU HAVE FULL SSH ACCESS TO THE SERVER and can run any command.
{context}

A user has now requested: "{request_text}"

IMPORTANT INSTRUCTIONS:
- You MUST respond in EXACTLY this format, with each line starting with the exact keywords below
- Do NOT use JSON, do NOT use code blocks, do NOT deviate from this format
- Each response must have these 3 lines:

DECISION: [COMMAND if user wants you to run something, or CONVERSATION if just talking]
COMMAND: [If DECISION is COMMAND, write the single shell command. If DECISION is CONVERSATION, write NONE]
RESPONSE: [Your analysis or conversation response]

Example 1 - Running a command:
User: "show me the current directory"
DECISION: COMMAND
COMMAND: pwd
RESPONSE: I'll show you the current directory using the pwd command.

Example 2 - Conversation:
User: "hello"
DECISION: CONVERSATION
COMMAND: NONE
RESPONSE: Hello! I'm {ai_name}, your {ai_role}. How can I help you today?
"""
            
            # Get AI response
            client = OllamaClient(host=ollama_url, model=model)
            success, ai_response = client.generate(prompt)
            
            if not success:
                GLib.idle_add(self.on_ai_error, ai_response)
                return
            
            # Parse AI response
            decision, command, response = self.parse_ai_response(ai_response)
            
            # Add AI response to chat
            GLib.idle_add(self.append_chat_message, ai_name.upper(), response, "ai")
            
            # Execute command if needed
            if decision == "COMMAND" and command and command != "NONE":
                # Show current directory with command
                current_dir = getattr(self.ssh_client, 'current_directory', None)
                if current_dir:
                    GLib.idle_add(self.append_chat_message, "COMMAND", f"[{current_dir}]$ {command}", "command")
                else:
                    GLib.idle_add(self.append_chat_message, "COMMAND", f"$ {command}", "command")
                
                success, output = self.ssh_client.execute_command(command)
                
                if success:
                    # Truncate very long output based on user setting (fallback to default)
                    max_output = self.saved_settings.get('max_output_chars', MAX_OUTPUT_CHARS)
                    try:
                        max_output = int(max_output)
                        if max_output < 0:
                            max_output = MAX_OUTPUT_CHARS
                    except Exception:
                        max_output = MAX_OUTPUT_CHARS
                    if len(output) > max_output:
                        output = output[:max_output] + f"\n... (output truncated, {len(output)} chars total)"
                    GLib.idle_add(self.append_chat_message, "OUTPUT", output or "(no output)", "output")
                    
                    # Show updated directory if it changed
                    new_dir = getattr(self.ssh_client, 'current_directory', None)
                    if new_dir and new_dir != current_dir:
                        GLib.idle_add(self.append_chat_message, "SYSTEM", f"Directory changed to: {new_dir}", "system")
                    
                    self.conversation_history.append({
                        "role": "assistant", 
                        "content": f"Executed: {command}\nOutput: {output}"
                    })
                else:
                    GLib.idle_add(self.append_chat_message, "ERROR", output, "system")
            else:
                self.conversation_history.append({
                    "role": "assistant", 
                    "content": response
                })
            
        except Exception as e:
            GLib.idle_add(self.on_ai_error, str(e))
        finally:
            GLib.idle_add(self.re_enable_input)
    
    def re_enable_input(self):
        """Re-enable input after processing"""
        self.send_btn.set_sensitive(True)
        self.input_entry.set_sensitive(True)
        self.input_entry.grab_focus()
        return False
    
    def parse_ai_response(self, response):
        """Parse AI response to extract decision, command, and response"""
        lines = response.strip().split('\n')
        decision = "CONVERSATION"
        command = "NONE"
        ai_message = ""
        response_started = False
        
        for line in lines:
            if line.startswith("DECISION:"):
                decision = line.replace("DECISION:", "").strip()
                response_started = False
            elif line.startswith("COMMAND:"):
                command = line.replace("COMMAND:", "").strip()
                response_started = False
            elif line.startswith("RESPONSE:"):
                ai_message = line.replace("RESPONSE:", "").strip()
                response_started = True
            elif response_started:
                # Continue capturing lines that are part of the response
                ai_message += "\n" + line
        
        return decision, command, ai_message
    
    def on_ai_error(self, error_msg):
        """Handle AI error"""
        self.append_chat_message("ERROR", error_msg, "system")
        self.re_enable_input()
        return False
    
    def on_clear_chat(self, button):
        """Clear chat history"""
        self.chat_buffer.set_text("")
        self.conversation_history.clear()
        self.append_chat_message("SYSTEM", "Chat cleared", "system")
    
    def show_error_dialog(self, message):
        """Show error dialog"""
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Error",
            body=message
        )
        dialog.add_response("ok", "OK")
        dialog.present()
    
    def load_settings(self):
        """Load saved settings"""
        self.saved_settings = self.settings_manager.load_settings()
        
        # Load SSH servers list
        self.ssh_servers = self.saved_settings.get('ssh_servers', [])
        
        # Populate quick server selector on main screen
        self.refresh_server_dropdown()
    
    def load_settings_to_dialog(self):
        """Load settings into the settings dialog entries"""
        if self.saved_settings:
            # Refresh server dropdown with saved servers
            self.refresh_server_dropdown()
            
            # Load last used server or first server
            last_server = self.saved_settings.get('last_server', '')
            if last_server and self.ssh_servers:
                # Try to select last used server
                for i in range(self.ssh_server_selector.get_model().__len__()):
                    self.ssh_server_selector.set_active(i)
                    if self.ssh_server_selector.get_active_text() == last_server:
                        break
            elif self.ssh_servers:
                # Select first server
                self.ssh_server_selector.set_active(1)  # 0 is <New Server>
            
            # Load Ollama and AI settings
            self.ollama_host_entry.set_text(self.saved_settings.get('ollama_url', 'http://localhost:11434'))
            self.ai_name_entry.set_text(self.saved_settings.get('ai_name', 'Jarvis'))
            self.ai_role_entry.set_text(self.saved_settings.get('ai_role', 'Linux Expert'))
            # Load max output chars (fallback to constant if missing)
            self.max_output_entry.set_text(str(self.saved_settings.get('max_output_chars', MAX_OUTPUT_CHARS)))
            
            # Load saved model selection
            saved_model = self.saved_settings.get('ollama_model', 'llama2')
            # Try to set the saved model as active
            model = self.model_selector.get_model()
            for i in range(len(model)):
                if self.model_selector.get_active_text() == saved_model:
                    break
                self.model_selector.set_active(i)
                if self.model_selector.get_active_text() == saved_model:
                    break
    
    def save_settings(self):
        """Save current settings"""
        if self.ssh_host_entry:  # Only save if settings dialog has been opened
            selected_model = self.model_selector.get_active_text()
            if not selected_model:
                selected_model = "llama2"
            
            # Get currently selected server name
            current_server = self.ssh_server_selector.get_active_text()
            if current_server and current_server != "<New Server>":
                last_server = current_server
            else:
                last_server = ""
            
            # Validate and save max_output_chars
            try:
                max_output_val = int(self.max_output_entry.get_text())
                if max_output_val < 0:
                    max_output_val = MAX_OUTPUT_CHARS
            except Exception:
                max_output_val = MAX_OUTPUT_CHARS

            settings = {
                'ssh_servers': self.ssh_servers,  # Save all servers
                'last_server': last_server,  # Remember last used server
                'ollama_url': self.ollama_host_entry.get_text(),
                'ollama_model': selected_model,
                'ai_name': self.ai_name_entry.get_text(),
                'ai_role': self.ai_role_entry.get_text(),
                'max_output_chars': max_output_val
            }
            
            self.saved_settings = settings
            self.settings_manager.save_settings(settings)
            self.append_chat_message("SYSTEM", f"Settings saved. Using model: {selected_model}", "system")
    
    def auto_connect_from_settings(self):
        """Auto-connect to SSH and Ollama if settings are saved"""
        if not self.saved_settings:
            return False
        
        # Auto-connect SSH to last used server
        last_server = self.saved_settings.get('last_server', '')
        ssh_servers = self.saved_settings.get('ssh_servers', [])
        
        if last_server and ssh_servers:
            # Find the last used server
            for server in ssh_servers:
                if server.get('name') == last_server:
                    ssh_host = server.get('host', '')
                    ssh_username = server.get('username', '')
                    ssh_password = server.get('password', '')
                    ssh_port = server.get('port', 22)
                    
                    if ssh_host and ssh_username and ssh_password:
                        self.append_chat_message("SYSTEM", f"Auto-connecting to {last_server}...", "system")
                        
                        def connect_thread():
                            self.ssh_client = SSHClient(ssh_host, ssh_username, ssh_password, port=ssh_port)
                            success, message = self.ssh_client.connect()
                            GLib.idle_add(self.on_auto_ssh_complete, success, message, last_server)
                        
                        thread = threading.Thread(target=connect_thread, daemon=True)
                        thread.start()
                    break
        
        # Auto-test Ollama connection
        ollama_url = self.saved_settings.get('ollama_url', '')
        if ollama_url:
            self.append_chat_message("SYSTEM", "Checking Ollama connection...", "system")
            
            def test_thread():
                client = OllamaClient(host=ollama_url)
                success, message = client.test_connection()
                GLib.idle_add(self.on_auto_ollama_complete, success, message)
            
            thread = threading.Thread(target=test_thread, daemon=True)
            thread.start()
        
        return False
    
    def auto_connect_ollama(self):
        """Auto-connect to Ollama"""
        ollama_url = self.saved_settings.get('ollama_url', 'http://localhost:11434')
        if ollama_url:
            self.append_chat_message("SYSTEM", "Checking Ollama connection...", "system")
            
            def test_thread():
                client = OllamaClient(host=ollama_url)
                success, message = client.test_connection()
                GLib.idle_add(self.on_auto_ollama_complete, success, message)
            
            thread = threading.Thread(target=test_thread, daemon=True)
            thread.start()
        
        return False
    
    def on_auto_ssh_complete(self, success, message, server_name=""):
        """Handle auto SSH connection result"""
        if success:
            self.local_mode = False
            self.ssh_status_label.set_label(f"SSH: ✓ {server_name}")
            self.append_chat_message("SYSTEM", f"Connected to {server_name}", "system")
        else:
            self.ssh_status_label.set_label("SSH: ✗ Failed")
            self.append_chat_message("SYSTEM", f"SSH auto-connect failed: {message}", "system")
        return False
    
    def on_auto_ollama_complete(self, success, message):
        """Handle auto Ollama test result"""
        if success:
            self.ollama_status_label.set_label("AI: ✓ Ready")
            saved_model = self.saved_settings.get('ollama_model', 'llama2')
            self.append_chat_message("SYSTEM", f"Ollama connected. Using model: {saved_model}", "system")
        else:
            self.ollama_status_label.set_label("AI: ✗ Failed")
            self.append_chat_message("SYSTEM", f"Ollama connection failed: {message}", "system")
        return False


class AITerminalApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.aiterminal.desktop",
                        flags=Gio.ApplicationFlags.FLAGS_NONE)
        
        self.create_action('quit', self.on_quit)
        self.create_action('about', self.on_about)
    
    def do_activate(self):
        """Activate the application"""
        win = self.props.active_window
        if not win:
            win = AITerminalWindow(application=self)
        win.present()
    
    def create_action(self, name, callback):
        """Create a GAction"""
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
    
    def on_quit(self, action, param):
        """Quit the application"""
        self.quit()
    
    def on_about(self, action, param):
        """Show about dialog"""
        about = Adw.AboutWindow(
            transient_for=self.props.active_window,
            application_name="AI Terminal Desktop",
            application_icon="utilities-terminal",
            developer_name="Fotios Tsiadimos",
            version=config.APP_VERSION,
            comments="Desktop AI Terminal with SSH and Ollama integration",
            website="https://github.com/ftsiadimos/aiterminal",
            license_type=Gtk.License.MIT_X11
        )
        about.present()


def main():
    """Main entry point"""
    app = AITerminalApp()
    return app.run(None)


if __name__ == "__main__":
    main()
