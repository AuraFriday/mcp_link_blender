# MCP-Link for Blender - Integration Module
# ==========================================
# Handles thread-safe integration between MCP client and Blender API
#
# This module provides:
# - Thread-safe execution of Blender API calls via bpy.app.timers
# - Python code execution with full bpy access
# - Direct API calls to bpy.ops, bpy.data, bpy.context
# - MCP tool calling from within Blender

import bpy
import json
import queue
import threading
import sys
import io
from typing import Dict, Any, Optional, List

from . import config
from .mcp_client import MCPClient


# Global state
mcp_client_instance: Optional[MCPClient] = None
blender_api_work_queue: queue.Queue = queue.Queue()
blender_api_processing_lock = threading.Lock()
python_sessions: Dict[str, Dict[str, Any]] = {}


def log(message: str, level: str = 'INFO'):
  """Thread-safe logging for MCP integration."""
  if config.DEBUG or level == 'ERROR':
    print(f"[MCP-Link] [{level}] {message}")


# =============================================================================
# Thread-Safe Blender API Execution
# =============================================================================

def _process_blender_api_work_queue() -> float:
  """
  Timer callback to process queued work on Blender's main thread.
  
  This function is registered with bpy.app.timers and runs every 0.1 seconds.
  It processes any pending work items from background MCP threads.
  """
  # Prevent reentrant calls
  if not blender_api_processing_lock.acquire(blocking=False):
    return 0.1
  
  try:
    while not blender_api_work_queue.empty():
      try:
        work_item = blender_api_work_queue.get_nowait()
        call_data = work_item['call_data']
        result_event = work_item['result_event']
        result_container = work_item['result_container']
        
        # Execute the tool call on main thread
        try:
          result = _handle_tool_call_on_main_thread(call_data)
          result_container['result'] = result
        except Exception as e:
          import traceback
          result_container['result'] = {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
          }
        
        # Signal completion
        result_event.set()
        
      except queue.Empty:
        break
  finally:
    blender_api_processing_lock.release()
  
  return 0.1  # Run again in 0.1 seconds


def _queue_blender_api_call(call_data: Dict[str, Any]) -> Dict[str, Any]:
  """
  Queue a Blender API call to be executed on the main thread.
  
  This is called from background MCP threads and blocks until the
  work is completed on Blender's main thread.
  """
  result_event = threading.Event()
  result_container: Dict[str, Any] = {}
  
  work_item = {
    'call_data': call_data,
    'result_event': result_event,
    'result_container': result_container,
  }
  
  blender_api_work_queue.put(work_item)
  
  # Wait for result (with timeout)
  if result_event.wait(timeout=300):  # 5 minute timeout
    return result_container.get('result', {'error': 'No result returned'})
  else:
    return {'error': 'Timeout waiting for Blender API call'}


# =============================================================================
# MCP Client Setup
# =============================================================================

def _create_mcp_client() -> MCPClient:
  """Create and configure the MCP client for Blender."""
  
  tool_description = """Blender MCP Tool - UNLIMITED API Access + Python Execution + MCP Integration

⚠️ MAXIMUM ACCESS MODE ⚠️
This tool gives AI COMPLETE, UNRESTRICTED access to:
- Entire Blender Python API (bpy.ops, bpy.data, bpy.context, bpy.types)
- Python execution with TRUE INLINE access to everything
- All other MCP tools (SQLite, browser, user, etc.)
- File system, network, system commands
- All loaded add-ons and global state

## Three Powerful Capabilities

### 1. Python Execution (RECOMMENDED - Most Powerful)

Execute arbitrary Python code with MAXIMUM access to Blender:

{
  "operation": "execute_python",
  "code": "import bpy\\nbpy.ops.mesh.primitive_cube_add(size=2)\\nprint(f'Created: {bpy.context.active_object.name}')",
  "session_id": "my_session",
  "persistent": true
}

Python code has access to:
- `bpy` - Full Blender Python API
- `mcp` - MCP bridge for calling other tools (sqlite, browser, user, etc.)
- `mathutils` - Blender's math utilities (Vector, Matrix, Quaternion, etc.)
- ALL standard Python libraries
- Session variables that persist across calls

Example - Create a donut with icing:
{
  "operation": "execute_python",
  "code": "import bpy\\n\\n# Create torus (donut base)\\nbpy.ops.mesh.primitive_torus_add(major_radius=1, minor_radius=0.4)\\ndonut = bpy.context.active_object\\ndonut.name = 'Donut'\\n\\n# Add subdivision surface\\nbpy.ops.object.modifier_add(type='SUBSURF')\\ndonut.modifiers['Subdivision'].levels = 2\\n\\nprint(f'Created delicious {donut.name}')"
}

### 2. Direct API Calls (Simple Operations)

For simple one-off operations:

{
  "operation": "api_call",
  "api_path": "bpy.ops.mesh.primitive_cube_add",
  "kwargs": {"size": 2, "location": [0, 0, 0]}
}

Supported paths:
- `bpy.ops.*` - All Blender operators
- `bpy.data.*` - Access to all Blender data (objects, meshes, materials, etc.)
- `bpy.context.*` - Current context (active object, selected objects, etc.)

### 3. MCP Tool Calling (Integration)

Call other MCP tools from Blender:

{
  "operation": "call_tool",
  "tool_name": "sqlite",
  "arguments": {
    "input": {
      "sql": "SELECT * FROM renders",
      "tool_unlock_token": "29e63eb5"
    }
  }
}

Available MCP tools: sqlite, browser, user, python, system, and more!

## Common Blender Operations

### Create Objects
```python
bpy.ops.mesh.primitive_cube_add(size=2)
bpy.ops.mesh.primitive_uv_sphere_add(radius=1)
bpy.ops.mesh.primitive_cylinder_add(radius=1, depth=2)
bpy.ops.mesh.primitive_torus_add(major_radius=1, minor_radius=0.25)
bpy.ops.mesh.primitive_monkey_add()  # Suzanne!
```

### Transform Objects
```python
obj = bpy.context.active_object
obj.location = (1, 2, 3)
obj.rotation_euler = (0, 0, 1.57)  # 90 degrees in radians
obj.scale = (2, 2, 2)
```

### Materials
```python
mat = bpy.data.materials.new("MyMaterial")
mat.use_nodes = True
mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (1, 0, 0, 1)  # Red
obj.data.materials.append(mat)
```

### Rendering
```python
bpy.context.scene.render.filepath = "/tmp/render.png"
bpy.ops.render.render(write_still=True)
```

### Animation
```python
obj.location = (0, 0, 0)
obj.keyframe_insert(data_path="location", frame=1)
obj.location = (5, 0, 0)
obj.keyframe_insert(data_path="location", frame=60)
```

## Persistent Sessions

Variables persist across multiple execute_python calls when using the same session_id:

Call 1:
{
  "operation": "execute_python",
  "code": "my_cube = bpy.context.active_object",
  "session_id": "design1",
  "persistent": true
}

Call 2:
{
  "operation": "execute_python", 
  "code": "my_cube.location.z += 2  # Uses variable from previous call",
  "session_id": "design1",
  "persistent": true
}

## Note

Blender must be running with the MCP-Link extension enabled.
The extension auto-connects to the MCP-Link server on startup.

⚠️ Python execution has FULL system access - use responsibly!
"""

  tool_readme = tool_description
  
  tool_schema = {
    "type": "object",
    "properties": {
      "operation": {
        "type": "string",
        "enum": ["execute_python", "api_call", "call_tool"],
        "description": "Operation type: 'execute_python', 'api_call', or 'call_tool'"
      },
      "code": {
        "type": "string",
        "description": "Python code to execute (for execute_python)"
      },
      "api_path": {
        "type": "string",
        "description": "API path like 'bpy.ops.mesh.primitive_cube_add' (for api_call)"
      },
      "args": {
        "type": "array",
        "description": "Positional arguments for api_call"
      },
      "kwargs": {
        "type": "object",
        "description": "Keyword arguments for api_call"
      },
      "tool_name": {
        "type": "string",
        "description": "MCP tool to call (for call_tool)"
      },
      "arguments": {
        "type": "object",
        "description": "Arguments for the MCP tool call"
      },
      "session_id": {
        "type": "string",
        "description": "Python session ID for persistent variables"
      },
      "persistent": {
        "type": "boolean",
        "description": "Whether to persist Python session variables"
      }
    },
    "required": ["operation"]
  }
  
  def tool_handler(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle incoming tool calls from AI agents."""
    return _queue_blender_api_call(arguments)
  
  return MCPClient(
    tool_name=config.TOOL_NAME,
    tool_description=tool_description,
    tool_readme=tool_readme,
    tool_schema=tool_schema,
    tool_handler=tool_handler,
    auto_reconnect=True
  )


# =============================================================================
# Tool Call Handlers
# =============================================================================

def _handle_tool_call_on_main_thread(call_data: Dict[str, Any]) -> Dict[str, Any]:
  """
  Dispatch tool calls on Blender's main thread.
  
  This is the central router for all incoming MCP requests.
  """
  operation = call_data.get('operation', 'execute_python')
  
  if operation == 'execute_python':
    return _handle_python_execution(call_data)
  elif operation == 'api_call':
    return _handle_api_call(call_data)
  elif operation == 'call_tool':
    return _handle_mcp_tool_call(call_data)
  else:
    return {
      'success': False,
      'error': f"Unknown operation: {operation}",
      'valid_operations': ['execute_python', 'api_call', 'call_tool']
    }


def _handle_python_execution(arguments: Dict[str, Any]) -> Dict[str, Any]:
  """
  Execute arbitrary Python code with full Blender API access.
  
  This is the "reflection" style interface that gives AI maximum power.
  """
  code = arguments.get('code', '')
  session_id = arguments.get('session_id', 'default')
  persistent = arguments.get('persistent', True)
  
  if not code:
    return {
      'success': False,
      'error': 'No code provided'
    }
  
  # Get or create session namespace
  if persistent and session_id in python_sessions:
    exec_namespace = python_sessions[session_id]
  else:
    exec_namespace = {
      '__builtins__': __builtins__,
      'bpy': bpy,
      'mcp': _create_mcp_bridge(),
    }
    
    # Add mathutils if available
    try:
      import mathutils
      exec_namespace['mathutils'] = mathutils
    except ImportError:
      pass
  
  # Capture stdout/stderr
  old_stdout = sys.stdout
  old_stderr = sys.stderr
  sys.stdout = captured_stdout = io.StringIO()
  sys.stderr = captured_stderr = io.StringIO()
  
  result = {
    'success': True,
    'stdout': '',
    'stderr': '',
    'session_id': session_id,
    'session_variables': []
  }
  
  try:
    # Execute the code
    exec(compile(code, "<ai-code>", "exec"), exec_namespace)
    
    # Store session if persistent
    if persistent:
      python_sessions[session_id] = exec_namespace
      
      # List user-defined variables
      result['session_variables'] = [
        k for k in exec_namespace.keys()
        if not k.startswith('_') and k not in ('bpy', 'mcp', 'mathutils', '__builtins__') and
        not hasattr(exec_namespace[k], '__module__') or
        (hasattr(exec_namespace[k], '__module__') and
        not exec_namespace[k].__module__.startswith('bpy') and
        not hasattr(exec_namespace[k], '__module__'))
      ]
    
  except Exception as e:
    import traceback
    result['success'] = False
    result['error'] = str(e)
    result['traceback'] = traceback.format_exc()
  
  finally:
    result['stdout'] = captured_stdout.getvalue()
    result['stderr'] = captured_stderr.getvalue()
    sys.stdout = old_stdout
    sys.stderr = old_stderr
  
  return result


def _handle_api_call(arguments: Dict[str, Any]) -> Dict[str, Any]:
  """
  Handle direct Blender API calls.
  
  Allows calling bpy.ops.*, bpy.data.*, bpy.context.* directly.
  """
  api_path = arguments.get('api_path', '')
  args = arguments.get('args', [])
  kwargs = arguments.get('kwargs', {})
  
  if not api_path:
    return {
      'success': False,
      'error': 'No api_path provided'
    }
  
  try:
    # Navigate to the target
    parts = api_path.split('.')
    
    if parts[0] != 'bpy':
      return {
        'success': False,
        'error': f"API path must start with 'bpy', got: {parts[0]}"
      }
    
    target = bpy
    for part in parts[1:]:
      target = getattr(target, part)
    
    # Call if callable
    if callable(target):
      result = target(*args, **kwargs)
      return {
        'success': True,
        'result': str(result) if result is not None else None
      }
    else:
      return {
        'success': True,
        'result': str(target)
      }
      
  except Exception as e:
    import traceback
    return {
      'success': False,
      'error': str(e),
      'traceback': traceback.format_exc()
    }


def _handle_mcp_tool_call(arguments: Dict[str, Any]) -> Dict[str, Any]:
  """
  Call other MCP tools from within Blender.
  
  This allows AI-executed code in Blender to access other tools
  like SQLite, browser automation, etc.
  """
  global mcp_client_instance
  
  tool_name = arguments.get('tool_name', '')
  tool_arguments = arguments.get('arguments', {})
  
  if not tool_name:
    return {
      'success': False,
      'error': 'No tool_name provided'
    }
  
  if not mcp_client_instance or not mcp_client_instance.is_connected:
    return {
      'success': False,
      'error': 'MCP client not connected'
    }
  
  result = mcp_client_instance.call_mcp_tool(tool_name, tool_arguments)
  return {
    'success': True,
    'result': result
  }


# =============================================================================
# MCP Bridge for Python Execution
# =============================================================================

class MCPBridge:
  """
  Bridge object injected into Python execution namespace.
  
  Allows AI-generated Python code to call other MCP tools.
  """
  
  def call(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Call another MCP tool.
    
    Example:
      result = mcp.call('sqlite', {'input': {'sql': 'SELECT * FROM data'}})
    """
    global mcp_client_instance
    
    if not mcp_client_instance or not mcp_client_instance.is_connected:
      return {'error': 'MCP client not connected'}
    
    return mcp_client_instance.call_mcp_tool(tool_name, arguments)


def _create_mcp_bridge() -> MCPBridge:
  """Create MCP bridge instance for Python execution."""
  return MCPBridge()


# =============================================================================
# Extension Lifecycle
# =============================================================================

def _auto_connect():
  """Initialize and connect the MCP client."""
  global mcp_client_instance
  
  log("Starting auto-connect to MCP server...")
  
  mcp_client_instance = _create_mcp_client()
  mcp_client_instance.start()
  
  # Check connection after a moment
  import time
  time.sleep(1)
  
  if mcp_client_instance.is_connected:
    log("[SUCCESS] Auto-connected to MCP server!")
  else:
    log("Auto-connect initiated - will keep retrying in background")


def start():
  """Start the MCP integration."""
  log("MCP Integration starting...")
  
  # Register the work queue processor timer
  if not bpy.app.timers.is_registered(_process_blender_api_work_queue):
    bpy.app.timers.register(_process_blender_api_work_queue, first_interval=0.1, persistent=True)
    log("Registered work queue processor timer")
  
  # Auto-connect if enabled
  if config.MCP_AUTO_CONNECT:
    # Check if we're in background mode (timers don't work well there)
    if bpy.app.background:
      # In background mode, connect immediately
      log("Background mode detected - connecting immediately")
      _auto_connect()
    else:
      # In GUI mode, delay slightly to let Blender finish loading
      def delayed_connect():
        _auto_connect()
        return None  # Don't repeat
      
      bpy.app.timers.register(delayed_connect, first_interval=1.0)
  else:
    log("MCP_AUTO_CONNECT is False - MCP integration disabled")
  
  log("MCP Integration started")


def stop():
  """Stop the MCP integration."""
  global mcp_client_instance
  
  log("MCP Integration stopping...")
  
  # Unregister timer
  if bpy.app.timers.is_registered(_process_blender_api_work_queue):
    bpy.app.timers.unregister(_process_blender_api_work_queue)
    log("Unregistered work queue processor timer")
  
  # Stop MCP client
  if mcp_client_instance:
    mcp_client_instance.stop()
    mcp_client_instance = None
  
  # Clear sessions
  python_sessions.clear()
  
  log("MCP Integration stopped")
