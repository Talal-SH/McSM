import functools
import time
import logging
import json
import os
from flask import jsonify, request, Blueprint, current_app

# Set up logging
logger = logging.getLogger(__name__)

# Create API blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

# API authentication middleware
def require_api_key(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # API key can be provided in header or as a query parameter
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            api_key = request.args.get('api_key')
        
        # Get configured API key from environment
        configured_api_key = current_app.config.get('API_KEY')
        
        # If no API key is configured, disable authentication
        if not configured_api_key:
            logger.warning('API authentication is disabled because no API key is configured')
            return f(*args, **kwargs)
        
        # Validate API key
        if api_key != configured_api_key:
            return jsonify({
                'success': False,
                'error': 'Invalid API key',
                'code': 401
            }), 401
        
        return f(*args, **kwargs)
    return decorated_function

# API rate limiting middleware
def rate_limit(f):
    # Simple in-memory rate limiting
    # In production, you would use Redis or another shared storage
    requests = {}
    
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # Get client IP
        client_ip = request.remote_addr
        
        # Check if rate limit is enabled
        rate_limit_enabled = current_app.config.get('RATE_LIMIT_ENABLED', False)
        if not rate_limit_enabled:
            return f(*args, **kwargs)
        
        # Get rate limit settings
        rate_limit_requests = current_app.config.get('RATE_LIMIT_REQUESTS', 60)
        rate_limit_window = current_app.config.get('RATE_LIMIT_WINDOW', 60)
        
        # Get current time
        current_time = time.time()
        
        # Clean up old requests
        for ip in list(requests.keys()):
            requests[ip] = [req for req in requests[ip] if current_time - req < rate_limit_window]
            if not requests[ip]:
                del requests[ip]
        
        # Check rate limit
        if client_ip in requests and len(requests[client_ip]) >= rate_limit_requests:
            return jsonify({
                'success': False,
                'error': 'Rate limit exceeded',
                'code': 429
            }), 429
        
        # Add request to history
        if client_ip not in requests:
            requests[client_ip] = []
        requests[client_ip].append(current_time)
        
        return f(*args, **kwargs)
    return decorated_function

# Health check endpoint (no authentication required)
@api_bp.route('/health', methods=['GET'])
def health_check():
    """API health check endpoint."""
    return jsonify({
        'status': 'ok',
        'version': current_app.config.get('VERSION', '1.0.0'),
        'timestamp': int(time.time())
    })

# Get all servers
@api_bp.route('/servers', methods=['GET'])
@require_api_key
def get_servers():
    """Get list of all servers."""
    from utils.server_detector import detect_servers
    
    servers = detect_servers(current_app.config['SERVERS_DIR'])
    
    # Add status information
    for server in servers:
        # Check if server is running
        server_manager = current_app.extensions.get('server_manager')
        if server_manager and server['id'] in server_manager.running_servers:
            server['status'] = 'running'
        else:
            server['status'] = 'stopped'
    
    return jsonify({
        'success': True,
        'servers': servers
    })

# Get server details
@api_bp.route('/servers/<server_id>', methods=['GET'])
@require_api_key
def get_server(server_id):
    """Get details for a specific server."""
    from utils.server_detector import detect_servers
    
    servers = detect_servers(current_app.config['SERVERS_DIR'])
    server = next((s for s in servers if s['id'] == server_id), None)
    
    if not server:
        return jsonify({
            'success': False,
            'error': 'Server not found',
            'code': 404
        }), 404
    
    # Add status information
    server_manager = current_app.extensions.get('server_manager')
    if server_manager and server['id'] in server_manager.running_servers:
        server['status'] = 'running'
    else:
        server['status'] = 'stopped'
    
    return jsonify({
        'success': True,
        'server': server
    })

# Start server
@api_bp.route('/servers/<server_id>/start', methods=['POST'])
@require_api_key
def start_server(server_id):
    """Start a server."""
    server_manager = current_app.extensions.get('server_manager')
    
    if not server_manager:
        return jsonify({
            'success': False,
            'error': 'Server manager not available',
            'code': 500
        }), 500
    
    success = server_manager.start_server(server_id)
    
    return jsonify({
        'success': success,
        'message': 'Server started successfully' if success else 'Failed to start server'
    })

# Stop server
@api_bp.route('/servers/<server_id>/stop', methods=['POST'])
@require_api_key
def stop_server(server_id):
    """Stop a server."""
    server_manager = current_app.extensions.get('server_manager')
    
    if not server_manager:
        return jsonify({
            'success': False,
            'error': 'Server manager not available',
            'code': 500
        }), 500
    
    success = server_manager.stop_server(server_id)
    
    return jsonify({
        'success': success,
        'message': 'Server stopped successfully' if success else 'Failed to stop server'
    })

# Send command to server
@api_bp.route('/servers/<server_id>/command', methods=['POST'])
@require_api_key
def send_command(server_id):
    """Send a command to a server."""
    server_manager = current_app.extensions.get('server_manager')
    
    if not server_manager:
        return jsonify({
            'success': False,
            'error': 'Server manager not available',
            'code': 500
        }), 500
    
    command = request.json.get('command')
    
    if not command:
        return jsonify({
            'success': False,
            'error': 'No command provided',
            'code': 400
        }), 400
    
    success = server_manager.send_command(server_id, command)
    
    return jsonify({
        'success': success,
        'message': 'Command sent successfully' if success else 'Failed to send command'
    })

# Create server
@api_bp.route('/servers', methods=['POST'])
@require_api_key
def create_server():
    """Create a new server."""
    server_creator = current_app.extensions.get('server_creator')
    
    if not server_creator:
        return jsonify({
            'success': False,
            'error': 'Server creator not available',
            'code': 500
        }), 500
    
    data = request.json
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'No data provided',
            'code': 400
        }), 400
    
    result = server_creator.create_server(
        server_name=data.get('name', 'New Server'),
        version_id=data.get('version', '1.20.4'),
        port=int(data.get('port', 25565)),
        memory=data.get('memory', '2G'),
        options=data.get('options', {})
    )
    
    return jsonify(result)

# Delete server
@api_bp.route('/servers/<server_id>', methods=['DELETE'])
@require_api_key
def delete_server(server_id):
    """Delete a server."""
    from utils.server_detector import detect_servers
    
    server_manager = current_app.extensions.get('server_manager')
    server_creator = current_app.extensions.get('server_creator')
    
    if not server_manager or not server_creator:
        return jsonify({
            'success': False,
            'error': 'Server management components not available',
            'code': 500
        }), 500
    
    # Check if server is running
    if server_id in server_manager.running_servers:
        # Stop the server first
        success = server_manager.stop_server(server_id)
        if not success:
            return jsonify({
                'success': False,
                'error': 'Could not stop the server before deletion',
                'code': 500
            }), 500
    
    # Get server name from ID
    servers = detect_servers(current_app.config['SERVERS_DIR'])
    server = next((s for s in servers if s['id'] == server_id), None)
    
    if not server:
        return jsonify({
            'success': False,
            'error': 'Server not found',
            'code': 404
        }), 404
    
    # Delete the server
    result = server_creator.delete_server(server['name'])
    
    return jsonify(result)

# Get server console output
@api_bp.route('/servers/<server_id>/console', methods=['GET'])
@require_api_key
def get_console(server_id):
    """Get the console output for a server."""
    server_manager = current_app.extensions.get('server_manager')
    
    if not server_manager:
        return jsonify({
            'success': False,
            'error': 'Server manager not available',
            'code': 500
        }), 500
    
    # Check if console buffer exists
    if server_id not in server_manager.console_buffers:
        return jsonify({
            'success': False,
            'error': 'Console buffer not found',
            'code': 404
        }), 404
    
    # Get last N lines (default 100)
    lines_count = min(int(request.args.get('lines', 100)), 1000)
    console_lines = server_manager.console_buffers[server_id][-lines_count:]
    
    return jsonify({
        'success': True,
        'lines': console_lines
    })

# Get available Minecraft versions
@api_bp.route('/versions', methods=['GET'])
@require_api_key
@rate_limit
def get_versions():
    """Get list of available Minecraft versions."""
    server_creator = current_app.extensions.get('server_creator')
    
    if not server_creator:
        return jsonify({
            'success': False,
            'error': 'Server creator not available',
            'code': 500
        }), 500
    
    versions = server_creator.get_available_versions()
    
    return jsonify({
        'success': True,
        'versions': versions
    })

def register_api(app, server_manager, server_creator):
    """Register API blueprint and extensions with the Flask app."""
    # Register extensions
    app.extensions['server_manager'] = server_manager
    app.extensions['server_creator'] = server_creator
    
    # Register blueprint
    app.register_blueprint(api_bp)