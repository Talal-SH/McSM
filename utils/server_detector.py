import os
import json
import logging
import re
import hashlib

logger = logging.getLogger(__name__)

def detect_servers(servers_dir):
    """
    Detect Minecraft servers in the specified directory.
    
    Args:
        servers_dir (str): Path to the directory containing server folders
        
    Returns:
        list: List of dictionaries containing server information
    """
    servers = []
    
    # Check if servers directory exists
    if not os.path.isdir(servers_dir):
        logger.warning(f"Servers directory '{servers_dir}' does not exist")
        return servers
    
    # List all directories in the servers directory
    for server_name in os.listdir(servers_dir):
        server_path = os.path.join(servers_dir, server_name)
        
        # Skip files, only process directories
        if not os.path.isdir(server_path):
            continue
        
        # Check if this directory contains a Minecraft server
        if is_minecraft_server(server_path):
            server_info = get_server_info(server_path, server_name)
            servers.append(server_info)
    
    return servers

def is_minecraft_server(server_path):
    """
    Check if the directory contains a Minecraft server.
    
    Args:
        server_path (str): Path to the server directory
        
    Returns:
        bool: True if the directory contains a Minecraft server, False otherwise
    """
    # Check for common Minecraft server files
    jar_files = [f for f in os.listdir(server_path) if f.endswith('.jar')]
    server_properties = os.path.isfile(os.path.join(server_path, 'server.properties'))
    eula_txt = os.path.isfile(os.path.join(server_path, 'eula.txt'))
    
    # If there are jar files and server.properties, it's likely a Minecraft server
    return len(jar_files) > 0 and server_properties

def get_server_info(server_path, server_name):
    """
    Get information about a Minecraft server.
    
    Args:
        server_path (str): Path to the server directory
        server_name (str): Name of the server directory
        
    Returns:
        dict: Dictionary containing server information
    """
    # Create a unique ID based on the server path
    server_id = hashlib.md5(server_path.encode('utf-8')).hexdigest()
    
    # Get the server type (vanilla, forge, paper, etc.)
    server_type = determine_server_type(server_path)
    
    # Get the server version
    server_version = determine_server_version(server_path, server_type)
    
    # Get the server properties
    properties = get_server_properties(server_path)
    
    # Check if the server has mods
    has_mods = os.path.isdir(os.path.join(server_path, 'mods')) and \
               len(os.listdir(os.path.join(server_path, 'mods'))) > 0
    
    # Count the number of mods if available
    mod_count = 0
    if has_mods:
        mod_count = len([f for f in os.listdir(os.path.join(server_path, 'mods')) 
                         if f.endswith('.jar')])
    
    # Check if the server has a world
    world_name = properties.get('level-name', 'world')
    has_world = os.path.isdir(os.path.join(server_path, world_name))
    
    # Return the server information
    return {
        'id': server_id,
        'name': server_name,
        'path': server_path,
        'type': server_type,
        'version': server_version,
        'properties': properties,
        'port': int(properties.get('server-port', 25565)),
        'has_mods': has_mods,
        'mod_count': mod_count,
        'has_world': has_world,
        'world_name': world_name,
        'max_players': int(properties.get('max-players', 20)),
        'motd': properties.get('motd', 'A Minecraft Server')
    }

def determine_server_type(server_path):
    """
    Determine the type of Minecraft server.
    
    Args:
        server_path (str): Path to the server directory
        
    Returns:
        str: Type of server (vanilla, forge, paper, etc.)
    """
    jar_files = [f for f in os.listdir(server_path) if f.endswith('.jar')]
    
    # Check for forge installer/universal jar
    if any('forge' in f.lower() for f in jar_files):
        return 'forge'
    
    # Check for fabric
    if any('fabric' in f.lower() for f in jar_files):
        return 'fabric'
    
    # Check for paper
    if any('paper' in f.lower() for f in jar_files):
        return 'paper'
    
    # Check for spigot
    if any('spigot' in f.lower() for f in jar_files):
        return 'spigot'
    
    # Check for bukkit
    if any('bukkit' in f.lower() for f in jar_files):
        return 'bukkit'
    
    # Default to vanilla
    return 'vanilla'

def determine_server_version(server_path, server_type):
    """
    Determine the Minecraft version of the server.
    
    Args:
        server_path (str): Path to the server directory
        server_type (str): Type of server
        
    Returns:
        str: Minecraft version or 'unknown'
    """
    # Try to determine version from jar file names
    jar_files = [f for f in os.listdir(server_path) if f.endswith('.jar')]
    
    for jar_file in jar_files:
        # Common version patterns in jar filenames
        version_match = re.search(r'[0-9]+\.[0-9]+(\.[0-9]+)?', jar_file)
        if version_match:
            return version_match.group(0)
    
    # If forge, try to read the version from forge version file
    if server_type == 'forge' and os.path.isfile(os.path.join(server_path, 'forge-version.properties')):
        try:
            with open(os.path.join(server_path, 'forge-version.properties'), 'r') as f:
                for line in f:
                    if line.startswith('forge.version='):
                        return line.split('=')[1].strip()
        except Exception as e:
            logger.error(f"Error reading forge version: {e}")
    
    return 'unknown'

def get_server_properties(server_path):
    """
    Read the server.properties file.
    
    Args:
        server_path (str): Path to the server directory
        
    Returns:
        dict: Dictionary of server properties
    """
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
    
    return properties