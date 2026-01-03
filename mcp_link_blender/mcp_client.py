# MCP-Link for Blender - MCP Client
# ==================================
# Handles communication with the MCP-Link server via SSE
#
# This module provides the MCPClient class that:
# - Discovers the MCP server via native messaging manifests
# - Establishes SSE connection for bidirectional communication
# - Registers the "blender" tool with the server
# - Handles incoming tool call requests from AI agents
# - Provides auto-reconnection with exponential backoff

import json
import threading
import time
import urllib.request
import urllib.error
import ssl
import os
import sys
from typing import Dict, Any, Optional, Callable

from . import config


def log(message: str, level: str = 'INFO'):
  """Thread-safe logging."""
  if config.DEBUG or level == 'ERROR':
    print(f"[MCP-Link] [{level}] [Client] {message}")


class MCPClient:
  """
  MCP Client for connecting Blender to the MCP-Link server.
  
  Uses the "reverse MCP" pattern where the client (Blender) connects
  to the server and registers itself as a remote tool.
  """
  
  def __init__(
    self,
    tool_name: str,
    tool_description: str,
    tool_readme: str,
    tool_schema: Dict[str, Any],
    tool_handler: Callable[[Dict[str, Any]], Dict[str, Any]],
    auto_reconnect: bool = True
  ):
    self.tool_name = tool_name
    self.tool_description = tool_description
    self.tool_readme = tool_readme
    self.tool_schema = tool_schema
    self.tool_handler = tool_handler
    self.auto_reconnect = auto_reconnect
    
    self.server_url: Optional[str] = None
    self.sse_connection: Optional[Dict[str, Any]] = None
    self.is_connected = False
    self.should_stop = False
    self.connection_thread: Optional[threading.Thread] = None
    self.retry_delay = 1  # Start with 1 second
    
    # SSL context that trusts local certificates
    self.ssl_context = ssl.create_default_context()
    self.ssl_context.check_hostname = False
    self.ssl_context.verify_mode = ssl.CERT_NONE
  
  def discover_server(self) -> Optional[str]:
    """
    Discover MCP server URL from native messaging manifest.
    
    The MCP-Link server writes its URL to a native messaging manifest
    that can be discovered by extensions/add-ins.
    """
    manifest_locations = []
    
    if sys.platform == 'win32':
      # Windows: Check AppData
      appdata = os.environ.get('LOCALAPPDATA', '')
      if appdata:
        manifest_locations.extend([
          os.path.join(appdata, 'AuraFriday', 'native-messaging', 'com.aurafriday.shim.json'),
          os.path.join(appdata, 'Google', 'Chrome', 'NativeMessagingHosts', 'com.aurafriday.shim.json'),
        ])
    elif sys.platform == 'darwin':
      # macOS
      home = os.path.expanduser('~')
      manifest_locations.extend([
        os.path.join(home, 'Library', 'Application Support', 'AuraFriday', 'native-messaging', 'com.aurafriday.shim.json'),
        os.path.join(home, 'Library', 'Application Support', 'Google', 'Chrome', 'NativeMessagingHosts', 'com.aurafriday.shim.json'),
      ])
    else:
      # Linux
      home = os.path.expanduser('~')
      manifest_locations.extend([
        os.path.join(home, '.config', 'aurafriday', 'native-messaging', 'com.aurafriday.shim.json'),
        os.path.join(home, '.config', 'google-chrome', 'NativeMessagingHosts', 'com.aurafriday.shim.json'),
      ])
    
    for manifest_path in manifest_locations:
      if os.path.exists(manifest_path):
        try:
          with open(manifest_path, 'r') as f:
            manifest = json.load(f)
            if 'sse_url' in manifest:
              log(f"Found MCP server at: {manifest['sse_url']}")
              return manifest['sse_url']
        except Exception as e:
          log(f"Error reading manifest {manifest_path}: {e}", 'ERROR')
    
    log("No MCP server manifest found", 'ERROR')
    return None
  
  def connect(self) -> bool:
    """Establish connection to MCP server."""
    if self.is_connected:
      return True
    
    # Discover server
    self.server_url = self.discover_server()
    if not self.server_url:
      return False
    
    log("=" * 60)
    log("MCP Client Connection Attempt")
    log("=" * 60)
    
    try:
      # Connect to SSE endpoint
      request = urllib.request.Request(
        self.server_url,
        headers={
          'Accept': 'text/event-stream',
          'Cache-Control': 'no-cache',
        }
      )
      
      response = urllib.request.urlopen(request, context=self.ssl_context, timeout=10)
      
      # Read initial connection data
      session_id = None
      for line in response:
        line = line.decode('utf-8').strip()
        if line.startswith('data:'):
          data = json.loads(line[5:].strip())
          if 'session_id' in data:
            session_id = data['session_id']
            break
        if line == '':
          break
      
      if not session_id:
        log("Failed to get session ID from server", 'ERROR')
        return False
      
      self.sse_connection = {
        'session_id': session_id,
        'response': response,
      }
      
      # Register the tool
      if not self._register_tool():
        return False
      
      self.is_connected = True
      self.retry_delay = 1  # Reset retry delay on successful connection
      
      log("=" * 60)
      log(f"[SUCCESS] {self.tool_name} registered successfully!")
      log("Listening for reverse tool calls...")
      log("=" * 60)
      
      return True
      
    except Exception as e:
      log(f"Connection failed: {e}", 'ERROR')
      return False
  
  def _register_tool(self) -> bool:
    """Register this tool with the MCP server."""
    if not self.sse_connection:
      return False
    
    register_url = self.server_url.replace('/sse', '/register-remote-tool')
    
    payload = {
      'session_id': self.sse_connection['session_id'],
      'tool_name': self.tool_name,
      'tool_description': self.tool_description,
      'tool_readme': self.tool_readme,
      'tool_schema': self.tool_schema,
    }
    
    try:
      request = urllib.request.Request(
        register_url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
      )
      
      response = urllib.request.urlopen(request, context=self.ssl_context, timeout=10)
      result = json.loads(response.read().decode('utf-8'))
      
      if result.get('success'):
        return True
      else:
        log(f"Registration failed: {result.get('error', 'Unknown error')}", 'ERROR')
        return False
        
    except Exception as e:
      log(f"Registration request failed: {e}", 'ERROR')
      return False
  
  def _send_response(self, request_id: str, result: Dict[str, Any]) -> bool:
    """Send response back to MCP server."""
    if not self.sse_connection:
      return False
    
    response_url = self.server_url.replace('/sse', '/remote-tool-response')
    
    payload = {
      'session_id': self.sse_connection['session_id'],
      'request_id': request_id,
      'result': result,
    }
    
    try:
      request = urllib.request.Request(
        response_url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
      )
      
      urllib.request.urlopen(request, context=self.ssl_context, timeout=30)
      return True
      
    except Exception as e:
      log(f"Failed to send response: {e}", 'ERROR')
      return False
  
  def call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Call another MCP tool from within Blender."""
    if not self.sse_connection:
      return None
    
    call_url = self.server_url.replace('/sse', '/call-tool')
    
    payload = {
      'session_id': self.sse_connection['session_id'],
      'tool_name': tool_name,
      'arguments': arguments,
    }
    
    try:
      request = urllib.request.Request(
        call_url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
      )
      
      response = urllib.request.urlopen(request, context=self.ssl_context, timeout=60)
      return json.loads(response.read().decode('utf-8'))
      
    except Exception as e:
      log(f"MCP tool call failed: {e}", 'ERROR')
      return {'error': str(e)}
  
  def _listen_for_requests(self):
    """Listen for incoming tool call requests from SSE stream."""
    while not self.should_stop and self.sse_connection:
      try:
        response = self.sse_connection['response']
        
        for line in response:
          if self.should_stop:
            break
          
          line = line.decode('utf-8').strip()
          
          if line.startswith('data:'):
            try:
              data = json.loads(line[5:].strip())
              
              if data.get('type') == 'tool_call':
                request_id = data.get('request_id')
                arguments = data.get('arguments', {})
                
                if config.MCP_DEBUG:
                  log(f"Received tool call: {request_id}")
                
                # Handle the tool call
                try:
                  result = self.tool_handler(arguments)
                  self._send_response(request_id, result)
                except Exception as e:
                  import traceback
                  error_result = {
                    'error': str(e),
                    'traceback': traceback.format_exc()
                  }
                  self._send_response(request_id, error_result)
              
              elif data.get('type') == 'ping':
                # Keepalive ping - no action needed
                pass
                
            except json.JSONDecodeError:
              pass
              
      except Exception as e:
        if not self.should_stop:
          log(f"SSE stream error: {e}", 'ERROR')
          self.is_connected = False
          break
    
    self.is_connected = False
  
  def _connection_worker(self):
    """Background worker for maintaining connection."""
    log("=" * 60)
    log("MCP Client Connection Worker Starting")
    log(f"Auto-reconnect enabled with exponential backoff")
    log("=" * 60)
    
    while not self.should_stop:
      if not self.is_connected:
        if self.connect():
          self._listen_for_requests()
        else:
          # Exponential backoff
          log(f"Retrying in {self.retry_delay} seconds...")
          time.sleep(self.retry_delay)
          self.retry_delay = min(self.retry_delay * 2, config.MAX_RETRY_DELAY)
      else:
        time.sleep(1)
    
    log("Connection worker stopped")
  
  def start(self):
    """Start the MCP client in a background thread."""
    if self.connection_thread and self.connection_thread.is_alive():
      return
    
    self.should_stop = False
    self.connection_thread = threading.Thread(
      target=self._connection_worker,
      daemon=True,
      name="MCP-Link-Client"
    )
    self.connection_thread.start()
  
  def stop(self):
    """Stop the MCP client."""
    self.should_stop = True
    self.is_connected = False
    
    if self.sse_connection and self.sse_connection.get('response'):
      try:
        self.sse_connection['response'].close()
      except:
        pass
    
    self.sse_connection = None
    
    if self.connection_thread:
      self.connection_thread.join(timeout=2)
