# McSM - Minecraft Server Manager

McSM is a web-based interface for managing multiple Minecraft servers running on your machine. It provides an easy way to start, stop, monitor, and configure your Minecraft servers from a single dashboard.

## Features

- 🔍 **Automatic Server Detection**: Place your server folders in the `servers/` directory, and McSM will automatically detect them
- 🚀 **Start/Stop Servers**: Control your servers with the click of a button
- 🖥️ **Live Console**: View real-time server console output and send commands
- ⚙️ **Server Properties**: Easily edit server properties and configurations
- 📂 **File Manager**: Browse and edit server files directly through the web interface
- 🧰 **Memory Management**: Adjust the amount of RAM allocated to each server

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- A Linux-based system (tested on Ubuntu and Arch Linux)
- Minecraft Java Edition servers

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/McSM.git
cd McSM
```

2. **Set up the virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Prepare your Minecraft servers**

Place your Minecraft server folders in the `servers/` directory. Each server should be in its own folder and include at least a server JAR file and a `server.properties` file.

```bash
mkdir -p servers
cp -r /path/to/your/server servers/my_server
```

5. **Run the application**

```bash
python app.py
```

6. **Access the web interface**

Open your browser and navigate to:
```
http://localhost:5000
```

## Usage Guide

### Dashboard

The dashboard displays all detected Minecraft servers with basic information:
- Server name
- Type (vanilla, forge, paper, etc.)
- Version
- Status (online/offline)
- Port

From here, you can:
- Start/stop servers
- Click "Manage" to access the detailed server management page

### Server Management

The server management page has three main tabs:

#### Console Tab

- View real-time server console output
- Send commands to the server
- Monitor server activity

#### Properties Tab

- Adjust server memory allocation
- Edit server.properties settings
- Save changes (note: most changes require a server restart)

#### Files Tab

- Browse server directories and files
- Edit configuration files
- Manage mods, plugins, and world files

## Configuration

McSM can be configured through environment variables:

### Basic Configuration

- `HOST`: Host to bind the web server to (default: 0.0.0.0)
- `PORT`: Port to run the web server on (default: 5000)
- `DEBUG`: Enable debug mode (default: True)
- `SECRET_KEY`: Secret key for session encryption (default: generated)
- `SERVERS_DIR`: Directory containing server folders (default: servers/)
- `DEFAULT_MEMORY`: Default memory allocation for servers (default: 2G)
- `MAX_MEMORY`: Maximum memory allocation for servers (default: 8G)
- `JAVA_PATH`: Path to Java executable (default: java)

### API Configuration

- `API_KEY`: Secret key for API authentication (default: empty, which disables auth)
- `RATE_LIMIT_ENABLED`: Enable API rate limiting (default: False)
- `RATE_LIMIT_REQUESTS`: Maximum requests per window (default: 60)
- `RATE_LIMIT_WINDOW`: Time window in seconds for rate limiting (default: 60)

### Discord Integration

- `DISCORD_WEBHOOK_URL`: Discord webhook URL for notifications
- `DISCORD_NOTIFICATIONS_ENABLED`: Enable Discord notifications (default: False)

You can set these variables in a `.env` file in the project root.

## Troubleshooting

### Server Not Detected

- Ensure your server folder contains a valid `server.properties` file
- Check that there's at least one `.jar` file in the server directory
- Verify file permissions allow the application to read the server directory

### Server Won't Start

- Ensure Java is installed and in your PATH (or configure `JAVA_PATH`)
- Check the server logs in the Console tab for specific error messages
- Verify that the server port is not already in use

### Console Not Updating

- Check that WebSocket connections are not blocked by a firewall
- Try refreshing the page

## Contributing

Contributions are welcome! Feel free to submit pull requests or open issues for bugs and feature requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## API Documentation

McSM provides a RESTful API that can be used to integrate with other applications, such as Discord bots.

### Authentication

API requests require an API key to be sent in the `X-API-Key` header or as an `api_key` query parameter.
To enable API authentication, set the `API_KEY` environment variable.

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/health` | GET | Health check endpoint (no auth required) |
| `/api/v1/servers` | GET | Get list of all servers |
| `/api/v1/servers/<server_id>` | GET | Get details for a specific server |
| `/api/v1/servers/<server_id>/start` | POST | Start a server |
| `/api/v1/servers/<server_id>/stop` | POST | Stop a server |
| `/api/v1/servers/<server_id>/command` | POST | Send a command to a server |
| `/api/v1/servers` | POST | Create a new server |
| `/api/v1/servers/<server_id>` | DELETE | Delete a server |
| `/api/v1/servers/<server_id>/console` | GET | Get the console output for a server |
| `/api/v1/versions` | GET | Get list of available Minecraft versions |

### Examples

**Get all servers:**
```bash
curl -H "X-API-Key: your_api_key" http://localhost:5000/api/v1/servers
```

**Start a server:**
```bash
curl -X POST -H "X-API-Key: your_api_key" http://localhost:5000/api/v1/servers/server_id/start
```

**Send a command to a server:**
```bash
curl -X POST -H "Content-Type: application/json" -H "X-API-Key: your_api_key" \
     -d '{"command":"say Hello from API"}' \
     http://localhost:5000/api/v1/servers/server_id/command
```

## Discord Bot Integration

McSM can be used as a backend for a Discord bot that allows managing Minecraft servers through Discord commands.
The API provides all the necessary endpoints to build a Discord bot that can:

1. List all Minecraft servers
2. Start and stop servers
3. Send commands to servers
4. View server status and console output

Example Discord.js bot code is available in the `examples/discord-bot` directory.

## Future Improvements

- User authentication for the web interface
- Server backups
- Performance monitoring
- Multi-user support
- Plugin/mod management interface
- Server templates
- Scheduled tasks (restarts, backups, etc.)
- Custom server icons
- Player statistics and monitoring
