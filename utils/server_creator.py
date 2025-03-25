import os
import json
import logging
import requests
import zipfile
import shutil
import time
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# Mojang's version manifest URL
VERSION_MANIFEST_URL = "https://launchermeta.mojang.com/mc/game/version_manifest.json"

class ServerCreator:
    """
    Utility class for creating new Minecraft servers.
    """
    
    def __init__(self, servers_dir):
        """
        Initialize the server creator.
        
        Args:
            servers_dir (str): Path to the directory where servers will be created
        """
        self.servers_dir = servers_dir
        self.cache_dir = os.path.join(os.path.dirname(servers_dir), 'cache')
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Cache file for version manifest
        self.manifest_cache_file = os.path.join(self.cache_dir, 'version_manifest.json')
        self.manifest_cache_time = 3600  # Cache for 1 hour

    def get_available_versions(self):
        """
        Get a list of available Minecraft versions.
        
        Returns:
            list: List of version dictionaries with 'id' and 'type' keys
        """
        manifest = self._get_version_manifest()
        
        if not manifest or 'versions' not in manifest:
            return []
        
        # Sort versions by release date (newest first)
        versions = sorted(
            manifest['versions'],
            key=lambda v: v.get('releaseTime', ''),
            reverse=True
        )
        
        # Extract relevant information
        return [
            {
                'id': version['id'],
                'type': version['type'],
                'release_time': version.get('releaseTime', '')
            }
            for version in versions
        ]

    def create_server(self, server_name, version_id, port=25565, memory='2G', options=None):
        """
        Create a new Minecraft server.
        
        Args:
            server_name (str): Name of the server (will be used as directory name)
            version_id (str): Minecraft version ID
            port (int): Server port
            memory (str): Memory allocation
            options (dict): Additional server options
            
        Returns:
            dict: Result of the operation with 'success' and 'message' keys
        """
        # Sanitize server name (only allow alphanumeric, dash, underscore)
        safe_name = ''.join(c for c in server_name if c.isalnum() or c in '-_')
        
        if not safe_name:
            return {'success': False, 'message': 'Invalid server name'}
        
        # Check if server directory already exists
        server_dir = os.path.join(self.servers_dir, safe_name)
        if os.path.exists(server_dir):
            return {'success': False, 'message': f'Server directory already exists: {safe_name}'}
        
        try:
            # Create server directory
            os.makedirs(server_dir)
            
            # Download server JAR
            jar_path = self._download_server_jar(version_id, server_dir)
            if not jar_path:
                shutil.rmtree(server_dir)
                return {'success': False, 'message': f'Failed to download server JAR for version {version_id}'}
            
            # Create initial server files
            self._create_server_properties(server_dir, port, options)
            self._create_eula_file(server_dir)
            self._create_mcsm_info(server_dir, memory, version_id)
            
            return {
                'success': True, 
                'message': f'Server created successfully: {safe_name}',
                'server_dir': server_dir,
                'server_name': safe_name
            }
            
        except Exception as e:
            logger.error(f"Error creating server: {e}")
            
            # Clean up if there was an error
            if os.path.exists(server_dir):
                shutil.rmtree(server_dir)
                
            return {'success': False, 'message': f'Error creating server: {str(e)}'}
    
    def delete_server(self, server_name):
        """
        Delete a Minecraft server.
        
        Args:
            server_name (str): Name of the server to delete
            
        Returns:
            dict: Result of the operation with 'success' and 'message' keys
        """
        server_dir = os.path.join(self.servers_dir, server_name)
        
        if not os.path.exists(server_dir):
            return {'success': False, 'message': f'Server not found: {server_name}'}
        
        try:
            shutil.rmtree(server_dir)
            return {'success': True, 'message': f'Server deleted successfully: {server_name}'}
        except Exception as e:
            logger.error(f"Error deleting server: {e}")
            return {'success': False, 'message': f'Error deleting server: {str(e)}'}

    def _get_version_manifest(self):
        """
        Get the Minecraft version manifest.
        
        Returns:
            dict: Version manifest JSON
        """
        # Check if we have a cached manifest that's still valid
        if os.path.exists(self.manifest_cache_file):
            file_age = time.time() - os.path.getmtime(self.manifest_cache_file)
            
            if file_age < self.manifest_cache_time:
                try:
                    with open(self.manifest_cache_file, 'r') as f:
                        return json.load(f)
                except Exception as e:
                    logger.error(f"Error reading cached manifest: {e}")
        
        # Download new manifest
        try:
            response = requests.get(VERSION_MANIFEST_URL)
            response.raise_for_status()
            
            manifest = response.json()
            
            # Cache the manifest
            with open(self.manifest_cache_file, 'w') as f:
                json.dump(manifest, f)
            
            return manifest
        except Exception as e:
            logger.error(f"Error downloading version manifest: {e}")
            return None

    def _get_version_info(self, version_id):
        """
        Get detailed information about a specific Minecraft version.
        
        Args:
            version_id (str): Minecraft version ID
            
        Returns:
            dict: Version information or None if not found
        """
        manifest = self._get_version_manifest()
        
        if not manifest or 'versions' not in manifest:
            return None
        
        # Find the version in the manifest
        version = next((v for v in manifest['versions'] if v['id'] == version_id), None)
        
        if not version or 'url' not in version:
            return None
        
        # Download version details
        try:
            response = requests.get(version['url'])
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error downloading version info for {version_id}: {e}")
            return None

    def _download_server_jar(self, version_id, server_dir):
        """
        Download the server JAR file for a specific Minecraft version.
        
        Args:
            version_id (str): Minecraft version ID
            server_dir (str): Path to the server directory
            
        Returns:
            str: Path to the downloaded JAR file, or None if download failed
        """
        # Check if we have a cached JAR
        cached_jar = os.path.join(self.cache_dir, f'minecraft_server.{version_id}.jar')
        
        if os.path.exists(cached_jar):
            # Copy cached JAR to server directory
            jar_path = os.path.join(server_dir, f'minecraft_server.{version_id}.jar')
            shutil.copy2(cached_jar, jar_path)
            return jar_path
        
        # Get version info
        version_info = self._get_version_info(version_id)
        
        if not version_info or 'downloads' not in version_info or 'server' not in version_info['downloads']:
            return None
        
        # Get server download URL
        download_url = version_info['downloads']['server']['url']
        
        # Download server JAR
        try:
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            # Save to cache
            with open(cached_jar, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Copy to server directory
            jar_path = os.path.join(server_dir, f'minecraft_server.{version_id}.jar')
            shutil.copy2(cached_jar, jar_path)
            
            return jar_path
        except Exception as e:
            logger.error(f"Error downloading server JAR for {version_id}: {e}")
            return None

    def _create_server_properties(self, server_dir, port, options=None):
        """
        Create the server.properties file.
        
        Args:
            server_dir (str): Path to the server directory
            port (int): Server port
            options (dict): Additional server options
        """
        properties_path = os.path.join(server_dir, 'server.properties')
        
        # Default server properties
        properties = {
            'server-port': str(port),
            'motd': 'A Minecraft Server managed by McSM',
            'enable-command-block': 'true',
            'spawn-protection': '0',
            'max-players': '20',
            'view-distance': '10',
            'spawn-npcs': 'true',
            'spawn-animals': 'true',
            'difficulty': 'normal',
            'gamemode': 'survival',
            'pvp': 'true',
            'hardcore': 'false',
            'enable-query': 'false',
            'enable-rcon': 'false',
            'generate-structures': 'true',
            'max-world-size': '29999984',
            'allow-nether': 'true',
            'allow-flight': 'false',
            'level-name': 'world',
            'level-type': 'default',
            'enforce-whitelist': 'false',
            'white-list': 'false',
            'online-mode': 'true',
            'prevent-proxy-connections': 'false',
            'network-compression-threshold': '256',
            'resource-pack-sha1': '',
            'resource-pack': '',
            'player-idle-timeout': '0',
            'force-gamemode': 'false',
            'rate-limit': '0',
            'snooper-enabled': 'true',
            'function-permission-level': '2',
            'spawn-monsters': 'true',
            'op-permission-level': '4',
            'use-native-transport': 'true',
            'max-tick-time': '60000',
            'max-build-height': '256',
            'spawn-animals': 'true'
        }
        
        # Update with user options
        if options:
            properties.update(options)
        
        # Write to file
        with open(properties_path, 'w') as f:
            for key, value in sorted(properties.items()):
                f.write(f"{key}={value}\n")

    def _create_eula_file(self, server_dir):
        """
        Create the eula.txt file (pre-accepted).
        
        Args:
            server_dir (str): Path to the server directory
        """
        eula_path = os.path.join(server_dir, 'eula.txt')
        
        with open(eula_path, 'w') as f:
            f.write("#By changing the setting below to TRUE you are indicating your agreement to our EULA (https://account.mojang.com/documents/minecraft_eula).\n")
            f.write("eula=true\n")

    def _create_mcsm_info(self, server_dir, memory, version):
        """
        Create the mcsm_info.json file with server metadata.
        
        Args:
            server_dir (str): Path to the server directory
            memory (str): Memory allocation
            version (str): Minecraft version
        """
        info_path = os.path.join(server_dir, 'mcsm_info.json')
        
        info = {
            'memory': memory,
            'version': version,
            'created_at': time.time(),
            'last_started': None,
            'total_runtime': 0
        }
        
        with open(info_path, 'w') as f:
            json.dump(info, f, indent=2)