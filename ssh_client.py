"""
SSH Client for AI Terminal Desktop
"""

import paramiko
import shlex
import re
import os
import time


class SSHClient:
    def __init__(self, host, username, password=None, key_file=None, port=22):
        self.host = host
        self.username = username
        self.password = password
        self.key_file = key_file
        self.port = port
        self.client = None
        self.connected = False
        self.current_directory = None  # Track current working directory
        self.running_channel = None  # Track currently running command channel
        
    def connect(self):
        """Connect to SSH server"""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if self.key_file:
                self.client.connect(
                    self.host, 
                    port=self.port, 
                    username=self.username, 
                    key_filename=self.key_file, 
                    timeout=10
                )
            else:
                self.client.connect(
                    self.host, 
                    port=self.port, 
                    username=self.username, 
                    password=self.password, 
                    timeout=10
                )
            
            self.connected = True
            
            # Get initial working directory
            try:
                stdin, stdout, stderr = self.client.exec_command('pwd')
                self.current_directory = stdout.read().decode('utf-8').strip()
            except:
                self.current_directory = None
            
            return True, "Connected successfully"
        except Exception as e:
            return False, str(e)
    
    def execute_command(self, command, output_callback=None, timeout=None):
        """Execute a command on the SSH server with optional streaming output.
        
        Args:
            command: Command to execute
            output_callback: Optional callback function(text) called for each chunk of output
            timeout: Optional timeout (not used in streaming mode)
        
        Returns:
            (success, output) tuple
        """
        try:
            if not self.connected or not self.client:
                return False, "Not connected"

            base_dir = self.current_directory
            
            def split_commands(cmd):
                parts = re.split(r'(;|&&)', cmd)
                result = []
                buf = ''
                for part in parts:
                    if part in (';', '&&'):
                        if buf.strip():
                            result.append(buf.strip())
                        result.append(part)
                        buf = ''
                    else:
                        buf += part
                if buf.strip():
                    result.append(buf.strip())
                return result

            # Track directory changes for all cd commands in the chain
            last_dir = base_dir
            cmds = split_commands(command)
            only_cd = True
            
            for part in cmds:
                if part in (';', '&&'):
                    continue
                if part.startswith('cd '):
                    try:
                        cd_parts = shlex.split(part)
                        if len(cd_parts) >= 2:
                            cd_target = cd_parts[1]
                            if last_dir:
                                exec_cmd = f'cd {shlex.quote(last_dir)} && cd {shlex.quote(cd_target)} && pwd'
                                stdin, stdout, stderr = self.client.exec_command(exec_cmd)
                                output = stdout.read().decode('utf-8')
                                error = stderr.read().decode('utf-8')
                                if output and not error:
                                    last_dir = output.strip().splitlines()[-1]
                                else:
                                    last_dir = os.path.normpath(os.path.join(last_dir, cd_target))
                                    break
                            else:
                                exec_cmd = f'cd {shlex.quote(cd_target)} && pwd'
                                stdin, stdout, stderr = self.client.exec_command(exec_cmd)
                                output = stdout.read().decode('utf-8')
                                error = stderr.read().decode('utf-8')
                                if output and not error:
                                    last_dir = output.strip().splitlines()[-1]
                                else:
                                    last_dir = os.path.normpath(cd_target)
                                    break
                    except Exception:
                        pass
                else:
                    only_cd = False
            
            # Update tracked directory
            if last_dir:
                self.current_directory = last_dir
            
            # If the command is only a single cd, don't run anything else
            if only_cd and len(cmds) == 1 and cmds[0].startswith('cd '):
                return True, last_dir
            
            # Build the full command
            if self.current_directory:
                full_command = f'cd {shlex.quote(self.current_directory)} && {command}'
            else:
                full_command = command
            
            # For streaming mode with callback
            if output_callback:
                return self._execute_streaming(full_command, output_callback)
            
            # Non-streaming mode (original behavior)
            stdin, stdout, stderr = self.client.exec_command(full_command)
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')
            result = output if output else error
            return True, result
            
        except Exception as e:
            return False, str(e)
    
    def _execute_streaming(self, command, output_callback):
        """Execute command with streaming output over SSH"""
        try:
            transport = self.client.get_transport()
            self.running_channel = transport.open_session()
            self.running_channel.get_pty()  # Request PTY for interactive commands
            self.running_channel.exec_command(command)
            
            all_output = []
            
            # Read output in chunks
            while True:
                if self.running_channel.recv_ready():
                    chunk = self.running_channel.recv(4096).decode('utf-8', errors='replace')
                    if chunk:
                        all_output.append(chunk)
                        output_callback(chunk)
                
                if self.running_channel.recv_stderr_ready():
                    chunk = self.running_channel.recv_stderr(4096).decode('utf-8', errors='replace')
                    if chunk:
                        all_output.append(chunk)
                        output_callback(chunk)
                
                # Check if command has finished
                if self.running_channel.exit_status_ready():
                    # Read any remaining output
                    while self.running_channel.recv_ready():
                        chunk = self.running_channel.recv(4096).decode('utf-8', errors='replace')
                        if chunk:
                            all_output.append(chunk)
                            output_callback(chunk)
                    break
                
                time.sleep(0.05)  # Small delay to avoid busy loop
            
            self.running_channel.close()
            self.running_channel = None
            
            return True, ''.join(all_output)
            
        except Exception as e:
            if self.running_channel:
                try:
                    self.running_channel.close()
                except:
                    pass
                self.running_channel = None
            return False, str(e)
    
    def interrupt_command(self):
        """Send interrupt signal (Ctrl+C) to running command"""
        if self.running_channel:
            try:
                # Send Ctrl+C character
                self.running_channel.send('\x03')
                return True
            except Exception:
                pass
        return False
    
    def kill_command(self):
        """Force close the running command channel"""
        if self.running_channel:
            try:
                self.running_channel.close()
                self.running_channel = None
                return True
            except Exception:
                pass
        return False
    
    def get_completions(self, partial_text):
        """Get bash tab completions for partial text"""
        try:
            if not self.connected or not self.client:
                return []
            
            # Escape special characters
            escaped_text = partial_text.replace("'", "'\\''")
            
            # Use bash's compgen for completion
            if self.current_directory:
                completion_cmd = f"cd {self.current_directory} && bash -c \"compgen -f -c -- '{escaped_text}' 2>/dev/null\""
            else:
                completion_cmd = f"bash -c \"compgen -f -c -- '{escaped_text}' 2>/dev/null\""
            
            stdin, stdout, stderr = self.client.exec_command(completion_cmd)
            output = stdout.read().decode('utf-8')
            
            if output:
                completions = [line.strip() for line in output.split('\n') if line.strip()]
                return completions
            return []
        except Exception as e:
            return []
    
    def disconnect(self):
        """Disconnect from SSH server"""
        if self.client:
            self.client.close()
            self.connected = False
