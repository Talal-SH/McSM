import os
import subprocess
import signal
import time
import logging
import threading
import re
import json
from utils.server_detector import detect_servers

logger = logging.getLogger(__name__)

class ServerManager:
    """
    Manages Minecraft server processes and provides utility functions.
    """
    
    def __init__(self, servers_dir, socketio):
        """
        Initialize the server manager.
        
        Args:
            servers_dir (str): Directory containing server folders
            socketio: SocketIO instance for real-time communication
        """
        self.servers_dir = servers_dir
        self.socketio = socketio
        self.running_servers = {}  # Dictionary of running server processes
        self.console_buffers = {}  # Console output buffers
        self.console_threads = {}  # Console reader threads

    def get_server_path(self, server_id):
        """
        Get the path to a server by its ID.
        
        Args:
            server_id (str): Server ID
            
        Returns:
            str: Path to the server directory, or None if not found
        """
        servers = detect_servers(self.servers_dir)
        for server in servers:
            if server['id'] == server_id:
                return server['path']
        return None

    def start_server(self, server_id):
        """
        Start a Minecraft server.
        
        Args:
            server_id (str): Server ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Check if server is already running
        if server_id in self.running_servers:
            logger.warning(f"Server {server_id} is already running")
            return False
        
        # Get server path
        server_path = self.get_server_path(server_id)
        if not server_path:
            logger.error(f"Server {server_id} not found")
            return False
        
        # Get server properties to determine memory settings
        properties = self.get_server_properties(server_id)
        
        # Find the server jar file
        jar_files = [f for f in os.listdir(server_path) if f.endswith('.jar')]
        if not jar_files:
            logger.error(f"No jar file found for server {server_id}")
            return False
        
        # Determine which jar file to use (prefer forge/fabric/etc. over vanilla)
        server_jar = None
        for jar in jar_files:
            if 'forge' in jar.lower() or 'fabric' in jar.lower() or 'paper' in jar.lower():
                server_jar = jar
                break
        
        # If no specific jar found, use the first one
        if not server_jar:
            server_jar = jar_files[0]
        
        # Build the Java command
        java_path = os.environ.get('JAVA_PATH', 'java')
        memory = properties.get('memory', '2G')
        
        command = [
            java_path,
            f'-Xmx{memory}',
            f'-Xms{memory}',
            '-jar',
            server_jar,
            'nogui'
        ]
        
        # Start the server process
        try:
            process = subprocess.Popen(
                command,
                cwd=server_path,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1  # Line-buffered
            )
            
            # Store the process
            self.running_servers[server_id] = process
            
            # Initialize console buffer
            self.console_buffers[server_id] = []
            
            # Start console reader thread
            self.console_threads[server_id] = threading.Thread(
                target=self._read_console,
                args=(server_id,),
                daemon=True
            )
            self.console_threads[server_id].start()
            
            logger.info(f"Started server {server_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting server {server_id}: {e}")
            return False

    def stop_server(self, server_id):
        """
        Stop a running Minecraft server.
        
        Args:
            server_id (str): Server ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        if server_id not in self.running_servers:
            logger.warning(f"Server {server_id} is not running")
            return False
        
        process = self.running_servers[server_id]
        
        # Send stop command to the server
        try:
            process.stdin.write("stop\n")
            process.stdin.flush()
            
            # Wait for the process to terminate (up to 30 seconds)
            for _ in range(30):
                if process.poll() is not None:
                    break
                time.sleep(1)
            
            # If server is still running, force kill it
            if process.poll() is None:
                logger.warning(f"Server {server_id} did not stop gracefully, forcing termination")
                process.terminate()
                process.wait(timeout=10)
            
            # Remove server from dictionaries
            del self.running_servers[server_id]
            
            # The console thread will detect the process termination and exit
            
            logger.info(f"Stopped server {server_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping server {server_id}: {e}")
            
            # Try to force kill the process if it's still running
            try:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=5)
                    del self.running_servers[server_id]
            except Exception:
                pass
                
            return False

    def get_server_status(self, server_id):
        """
        Get the status of a server.
        
        Args:
            server_id (str): Server ID
            
        Returns:
            dict: Server status information
        """
        is_running = server_id in self.running_servers
        
        # Get server info
        servers = detect_servers(self.servers_dir)
        server_info = next((s for s in servers if s['id'] == server_id), None)
        
        if not server_info:
            return {'error': 'Server not found'}
        
        # Get last console lines if available
        last_console_lines = []
        if server_id in self.console_buffers:
            last_console_lines = self.console_buffers[server_id][-20:]  # Last 20 lines
        
        return {
            'id': server_id,
            'name': server_info['name'],
            'running': is_running,
            'uptime': self._get_server_uptime(server_id) if is_running else 0,
            'console': last_console_lines
        }

    def _get_server_uptime(self, server_id):
        """
        Get the uptime of a running server in seconds.
        
        Args:
            server_id (str): Server ID
            
        Returns:
            int: Uptime in seconds, or 0 if not running
        """
        # This would need to track server start time
        # For now, just return 0
        return 0

    def get_server_properties(self, server_id):
        """
        Get the server.properties file content.
        
        Args:
            server_id (str): Server ID
            
        Returns:
            dict: Server properties
        """
        server_path = self.get_server_path(server_id)
        if not server_path:
            return {}
        
        properties = {}
        properties_path = os.path.join(server_path, 'server.properties')
        
        if os.path.isfile(properties_path):
            try:
                with open(properties_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            key_value = line.split('=', 1)
                            if len(key_value) == 2:
                                key, value = key_value
                                properties[key.strip()] = value.strip()
            except Exception as e:
                logger.error(f"Error reading server properties: {e}")
        
        # Add memory setting if available
        server_info_path = os.path.join(server_path, 'mcsm_info.json')
        if os.path.isfile(server_info_path):
            try:
                with open(server_info_path, 'r') as f:
                    server_info = json.load(f)
                    if 'memory' in server_info:
                        properties['memory'] = server_info['memory']
            except Exception as e:
                logger.error(f"Error reading server info: {e}")
        
        # Default memory if not set
        if 'memory' not in properties:
            properties['memory'] = os.environ.get('DEFAULT_MEMORY', '2G')
        
        return properties

    def update_server_properties(self, server_id, properties):
        """
        Update the server.properties file.
        
        Args:
            server_id (str): Server ID
            properties (dict): Properties to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        server_path = self.get_server_path(server_id)
        if not server_path:
            return False
        
        properties_path = os.path.join(server_path, 'server.properties')
        
        # Check if server is running
        if server_id in self.running_servers:
            logger.warning(f"Cannot update properties while server {server_id} is running")
            return False
        
        # Handle memory setting separately
        memory = properties.pop('memory', None)
        if memory:
            # Save memory setting to a separate file
            server_info_path = os.path.join(server_path, 'mcsm_info.json')
            try:
                # Load existing info if file exists
                server_info = {}
                if os.path.isfile(server_info_path):
                    with open(server_info_path, 'r') as f:
                        server_info = json.load(f)
                
                # Update memory setting
                server_info['memory'] = memory
                
                # Save updated info
                with open(server_info_path, 'w') as f:
                    json.dump(server_info, f, indent=2)
            except Exception as e:
                logger.error(f"Error updating server info: {e}")
                return False
        
        # Read existing properties
        existing_properties = {}
        try:
            if os.path.isfile(properties_path):
                with open(properties_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            key_value = line.split('=', 1)
                            if len(key_value) == 2:
                                key, value = key_value
                                existing_properties[key.strip()] = value.strip()
        except Exception as e:
            logger.error(f"Error reading server properties: {e}")
            return False
        
        # Update properties
        existing_properties.update(properties)
        
        # Write properties back to file
        try:
            with open(properties_path, 'w') as f:
                for key, value in sorted(existing_properties.items()):
                    f.write(f"{key}={value}\n")
            return True
        except Exception as e:
            logger.error(f"Error writing server properties: {e}")
            return False

    def list_server_files(self, server_id, path=''):
        """
        List files in a server directory.
        
        Args:
            server_id (str): Server ID
            path (str): Relative path within the server directory
            
        Returns:
            list: List of file information dictionaries
        """
        server_path = self.get_server_path(server_id)
        if not server_path:
            return []
        
        # Sanitize and resolve the requested path
        requested_path = os.path.normpath(os.path.join(server_path, path))
        
        # Ensure the path is within the server directory
        if not requested_path.startswith(server_path):
            logger.warning(f"Attempted to access path outside server directory: {requested_path}")
            return []
        
        # Check if path exists
        if not os.path.exists(requested_path):
            return []
        
        # If path is a file, return file info
        if os.path.isfile(requested_path):
            return [{
                'name': os.path.basename(requested_path),
                'path': os.path.relpath(requested_path, server_path),
                'type': 'file',
                'size': os.path.getsize(requested_path)
            }]
        
        # List directory contents
        files = []
        try:
            for item in os.listdir(requested_path):
                item_path = os.path.join(requested_path, item)
                item_type = 'directory' if os.path.isdir(item_path) else 'file'
                
                # Skip certain directories like .git
                if item.startswith('.'):
                    continue
                
                files.append({
                    'name': item,
                    'path': os.path.relpath(item_path, server_path),
                    'type': item_type,
                    'size': os.path.getsize(item_path) if item_type == 'file' else 0
                })
        except Exception as e:
            logger.error(f"Error listing files: {e}")
        
        return sorted(files, key=lambda x: (x['type'] == 'file', x['name']))

    def get_server_file(self, server_id, path):
        """
        Get the content of a server file.
        
        Args:
            server_id (str): Server ID
            path (str): Relative path to the file
            
        Returns:
            str: File content, or empty string if file cannot be read
        """
        server_path = self.get_server_path(server_id)
        if not server_path:
            return ""
        
        # Sanitize and resolve the requested path
        file_path = os.path.normpath(os.path.join(server_path, path))
        
        # Ensure the path is within the server directory
        if not file_path.startswith(server_path):
            logger.warning(f"Attempted to access file outside server directory: {file_path}")
            return ""
        
        # Check if file exists and is a file
        if not os.path.isfile(file_path):
            return ""
        
        # Check if file is binary (avoid returning binary content)
        if self._is_binary_file(file_path):
            return "Binary file - cannot display content"
        
        # Read file content
        try:
            with open(file_path, 'r', errors='replace') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return ""

    def update_server_file(self, server_id, path, content):
        """
        Update the content of a server file.
        
        Args:
            server_id (str): Server ID
            path (str): Relative path to the file
            content (str): New file content
            
        Returns:
            bool: True if successful, False otherwise
        """
        server_path = self.get_server_path(server_id)
        if not server_path:
            return False
        
        # Sanitize and resolve the requested path
        file_path = os.path.normpath(os.path.join(server_path, path))
        
        # Ensure the path is within the server directory
        if not file_path.startswith(server_path):
            logger.warning(f"Attempted to access file outside server directory: {file_path}")
            return False
        
        # Check if file is binary (avoid writing to binary files)
        if os.path.exists(file_path) and self._is_binary_file(file_path):
            logger.warning(f"Attempted to write to binary file: {file_path}")
            return False
        
        # Write file content
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w') as f:
                f.write(content)
            return True
        except Exception as e:
            logger.error(f"Error writing file {file_path}: {e}")
            return False

    def _is_binary_file(self, file_path, sample_size=1024):
        """
        Check if a file is a binary file.
        
        Args:
            file_path (str): Path to the file
            sample_size (int): Number of bytes to check
            
        Returns:
            bool: True if the file is binary, False otherwise
        """
        try:
            with open(file_path, 'rb') as f:
                sample = f.read(sample_size)
                # Check for null bytes
                if b'\0' in sample:
                    return True
                
                # Check for high proportion of non-printable characters
                non_printable = sum(1 for byte in sample if byte < 32 and byte not in (9, 10, 13))
                return non_printable / len(sample) > 0.3 if sample else False
        except Exception:
            return False

    def attach_console(self, server_id):
        """
        Attach to a server's console output.
        
        Args:
            server_id (str): Server ID
        """
        # Send the console buffer to the client
        if server_id in self.console_buffers:
            for line in self.console_buffers[server_id]:
                self.socketio.emit('console_output', {
                    'server_id': server_id,
                    'line': line
                })

    def send_command(self, server_id, command):
        """
        Send a command to a running server.
        
        Args:
            server_id (str): Server ID
            command (str): Command to send
            
        Returns:
            bool: True if successful, False otherwise
        """
        if server_id not in self.running_servers:
            logger.warning(f"Server {server_id} is not running")
            return False
        
        process = self.running_servers[server_id]
        
        try:
            process.stdin.write(f"{command}\n")
            process.stdin.flush()
            return True
        except Exception as e:
            logger.error(f"Error sending command to server {server_id}: {e}")
            return False

    def _read_console(self, server_id):
        """
        Read console output from a running server process.
        
        Args:
            server_id (str): Server ID
        """
        if server_id not in self.running_servers:
            return
        
        process = self.running_servers[server_id]
        
        try:
            # Read lines from the process output
            for line in iter(process.stdout.readline, ''):
                line = line.rstrip()
                
                # Store line in buffer
                self.console_buffers[server_id].append(line)
                
                # Keep buffer at reasonable size
                if len(self.console_buffers[server_id]) > 1000:
                    self.console_buffers[server_id] = self.console_buffers[server_id][-1000:]
                
                # Emit line to connected clients
                self.socketio.emit('console_output', {
                    'server_id': server_id,
                    'line': line
                })
                
                # Check if process is still running
                if process.poll() is not None:
                    break
            
            # Process has terminated
            if server_id in self.running_servers:
                del self.running_servers[server_id]
                
            # Emit termination notice
            self.socketio.emit('server_stopped', {
                'server_id': server_id
            })
            
        except Exception as e:
            logger.error(f"Error reading console output: {e}")