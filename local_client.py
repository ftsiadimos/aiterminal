"""
Local Terminal Client for AI Terminal Desktop
Executes commands locally without SSH
"""

import subprocess
import os
import shlex
import signal


class LocalClient:
    def __init__(self):
        self.connected = True  # Always connected for local mode
        self.current_directory = os.getcwd()
        self.running_process = None  # Track currently running process
        
    def connect(self):
        """Connect (always succeeds for local mode)"""
        self.current_directory = os.getcwd()
        return True, "Connected to local terminal"
    
    def execute_command(self, command, output_callback=None, timeout=None):
        """Execute a command locally with optional streaming output
        
        Args:
            command: Command to execute
            output_callback: Optional callback function(text) called for each chunk of output
            timeout: Optional timeout in seconds (None = no timeout for streaming)
        
        Returns:
            (success, output) tuple
        """
        try:
            # Check if this is a cd command
            command_stripped = command.strip()
            if command_stripped.lower().startswith('cd '):
                # Handle cd command specially
                path = command_stripped[3:].strip()
                if not path:
                    path = os.path.expanduser('~')
                else:
                    path = os.path.expanduser(path)
                
                # Make path absolute if relative
                if not os.path.isabs(path):
                    path = os.path.join(self.current_directory, path)
                
                try:
                    os.chdir(path)
                    self.current_directory = os.getcwd()
                    return True, ""
                except FileNotFoundError:
                    return True, f"cd: {path}: No such file or directory"
                except PermissionError:
                    return True, f"cd: {path}: Permission denied"
                except Exception as e:
                    return True, f"cd: {str(e)}"
            
            # For streaming mode with callback
            if output_callback:
                return self._execute_streaming(command, output_callback)
            
            # Non-streaming mode (original behavior)
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.current_directory,
                capture_output=True,
                text=True,
                timeout=timeout or 30
            )
            
            # Combine stdout and stderr
            output = result.stdout
            if result.stderr:
                output += result.stderr
            
            return True, output or ""
        except subprocess.TimeoutExpired:
            return False, "Command timed out (30 seconds)"
        except Exception as e:
            return False, str(e)
    
    def _execute_streaming(self, command, output_callback):
        """Execute command with streaming output"""
        try:
            # Start process with unbuffered output
            self.running_process = subprocess.Popen(
                command,
                shell=True,
                cwd=self.current_directory,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,  # Line buffered
                preexec_fn=os.setsid  # Create new process group for signal handling
            )
            
            all_output = []
            
            # Read output line by line
            try:
                for line in iter(self.running_process.stdout.readline, ''):
                    if line:
                        all_output.append(line)
                        output_callback(line)
                    if self.running_process.poll() is not None:
                        break
            except Exception:
                pass
            
            # Wait for process to complete
            self.running_process.wait()
            return_code = self.running_process.returncode
            self.running_process = None
            
            return True, ''.join(all_output)
            
        except Exception as e:
            self.running_process = None
            return False, str(e)
    
    def interrupt_command(self):
        """Send interrupt signal (Ctrl+C) to running command"""
        if self.running_process:
            try:
                # Send SIGINT to the process group
                os.killpg(os.getpgid(self.running_process.pid), signal.SIGINT)
                return True
            except Exception:
                try:
                    # Fallback: terminate the process
                    self.running_process.terminate()
                    return True
                except Exception:
                    pass
        return False
    
    def kill_command(self):
        """Force kill running command"""
        if self.running_process:
            try:
                os.killpg(os.getpgid(self.running_process.pid), signal.SIGKILL)
                return True
            except Exception:
                try:
                    self.running_process.kill()
                    return True
                except Exception:
                    pass
        return False
    
    def get_completions(self, partial_text):
        """Get bash tab completions for partial text"""
        try:
            # Escape special characters
            escaped_text = partial_text.replace("'", "'\\''")
            
            # Use bash's compgen for completion
            completion_cmd = f"bash -c \"compgen -f -c -- '{escaped_text}' 2>/dev/null\""
            
            result = subprocess.run(
                completion_cmd,
                shell=True,
                cwd=self.current_directory,
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.stdout:
                completions = [line.strip() for line in result.stdout.split('\n') if line.strip()]
                return completions
            return []
        except Exception as e:
            return []
    
    def disconnect(self):
        """Disconnect (kill any running process)"""
        self.kill_command()
