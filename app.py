from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_socketio import SocketIO, emit
import os
import json
import shutil
import subprocess
import time
import logging
from utils.server_detector import detect_servers
from utils.server_manager import ServerManager
from utils.server_creator import ServerCreator
from utils.api import register_api
from config import Config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Initialize Flask application
app = Flask(__name__)
app.config.from_object(Config)
socketio = SocketIO(app)

# Initialize server manager and creator
server_manager = ServerManager(app.config['SERVERS_DIR'], socketio)
server_creator = ServerCreator(app.config['SERVERS_DIR'])

@app.route('/')
def index():
    """Render the main dashboard page."""
    servers = detect_servers(app.config['SERVERS_DIR'])
    return render_template('index.html', servers=servers)

@app.route('/server/<server_id>')
def server_detail(server_id):
    """Render the server detail page."""
    servers = detect_servers(app.config['SERVERS_DIR'])
    server = next((s for s in servers if s['id'] == server_id), None)
    
    if not server:
        return redirect(url_for('index'))
    
    return render_template('server_detail.html', server=server)

@app.route('/api/servers')
def get_servers():
    """API endpoint to get all servers."""
    servers = detect_servers(app.config['SERVERS_DIR'])
    return jsonify(servers)

@app.route('/api/server/<server_id>/start', methods=['POST'])
def start_server(server_id):
    """API endpoint to start a server."""
    success = server_manager.start_server(server_id)
    return jsonify({'success': success})

@app.route('/api/server/<server_id>/stop', methods=['POST'])
def stop_server(server_id):
    """API endpoint to stop a server."""
    success = server_manager.stop_server(server_id)
    return jsonify({'success': success})

@app.route('/api/server/<server_id>/status')
def server_status(server_id):
    """API endpoint to get server status."""
    status = server_manager.get_server_status(server_id)
    return jsonify(status)

@app.route('/api/server/<server_id>/properties', methods=['GET', 'POST'])
def server_properties(server_id):
    """API endpoint to get or update server properties."""
    if request.method == 'POST':
        properties = request.json
        success = server_manager.update_server_properties(server_id, properties)
        return jsonify({'success': success})
    else:
        properties = server_manager.get_server_properties(server_id)
        return jsonify(properties)

@app.route('/api/server/<server_id>/files', methods=['GET'])
def list_server_files(server_id):
    """API endpoint to list server files."""
    path = request.args.get('path', '')
    files = server_manager.list_server_files(server_id, path)
    return jsonify(files)

@app.route('/api/server/<server_id>/file', methods=['GET', 'POST'])
def server_file(server_id):
    """API endpoint to get or update a server file."""
    path = request.args.get('path', '')
    
    if request.method == 'POST':
        content = request.json.get('content', '')
        success = server_manager.update_server_file(server_id, path, content)
        return jsonify({'success': success})
    else:
        content = server_manager.get_server_file(server_id, path)
        return jsonify({'content': content})

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection."""
    logger.info('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection."""
    logger.info('Client disconnected')

@socketio.on('join_server')
def handle_join_server(data):
    """Handle joining a server's console room."""
    server_id = data.get('server_id')
    if server_id:
        server_manager.attach_console(server_id)

@socketio.on('command')
def handle_command(data):
    """Handle console command execution."""
    server_id = data.get('server_id')
    command = data.get('command')
    if server_id and command:
        server_manager.send_command(server_id, command)

@app.route('/create')
def create_server_page():
    """Render the server creation page."""
    versions = server_creator.get_available_versions()
    return render_template('create_server.html', versions=versions)

@app.route('/api/servers/create', methods=['POST'])
def create_server():
    """API endpoint to create a new server."""
    data = request.json
    result = server_creator.create_server(
        server_name=data.get('name', 'New Server'),
        version_id=data.get('version', '1.20.4'),
        port=int(data.get('port', 25565)),
        memory=data.get('memory', '2G'),
        options=data.get('options', {})
    )
    return jsonify(result)

@app.route('/api/servers/available-versions')
def get_available_versions():
    """API endpoint to get available Minecraft versions."""
    versions = server_creator.get_available_versions()
    return jsonify(versions)

@app.route('/api/server/<server_id>/delete', methods=['POST'])
def delete_server(server_id):
    """API endpoint to delete a server."""
    # First check if server is running
    if server_id in server_manager.running_servers:
        # Stop the server first
        success = server_manager.stop_server(server_id)
        if not success:
            return jsonify({'success': False, 'message': 'Could not stop the server before deletion'})
    
    # Get server name from ID
    servers = detect_servers(app.config['SERVERS_DIR'])
    server = next((s for s in servers if s['id'] == server_id), None)
    
    if not server:
        return jsonify({'success': False, 'message': 'Server not found'})
    
    # Delete the server
    result = server_creator.delete_server(server['name'])
    return jsonify(result)

# Register the API
register_api(app, server_manager, server_creator)

if __name__ == '__main__':
    # Ensure the servers directory exists
    os.makedirs(app.config['SERVERS_DIR'], exist_ok=True)
    
    # Create cache directory for server downloads
    os.makedirs(os.path.join(os.path.dirname(app.config['SERVERS_DIR']), 'cache'), exist_ok=True)
    
    # Log API key status
    if app.config.get('API_KEY'):
        logger.info("API authentication is enabled")
    else:
        logger.warning("API authentication is disabled - configure API_KEY for security")
    
    # Start the Flask application with SocketIO
    socketio.run(app, host=app.config['HOST'], port=app.config['PORT'], debug=app.config['DEBUG'])