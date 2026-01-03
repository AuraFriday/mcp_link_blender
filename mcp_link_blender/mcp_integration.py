"""
File: mcp_integration.py
Project: MCP-Link Blender Extension
Component: MCP Integration - Core infrastructure for connecting Blender to MCP-Link server
Author: Christopher Nathan Drake (cnd)
Created: 2025-01-03
SPDX-License-Identifier: GPL-3.0-or-later
Copyright: (c) 2025 Christopher Nathan Drake. All rights reserved.

This module provides the core MCP integration functionality:
- Auto-connects to MCP server on extension startup
- Registers Blender as a remote tool
- Handles incoming tool calls via generic Python executor
- Thread-safe execution using Blender's timer system

The AI gets MAXIMUM ACCESS to Blender - it can execute any Python code,
call any bpy.ops operator, access any bpy.data, and more.
"""

import bpy
import os
import sys
import json
import queue
import threading
import time
import traceback
from typing import Dict, Any, Optional

from . import config
from .mcp_client import MCPClient

# Global MCP client instance
mcp_client_instance: Optional[MCPClient] = None

# Python execution sessions (persist variables across executions)
python_sessions: Dict[str, Dict[str, Any]] = {}

# Thread-safe work queue for API calls from daemon threads
blender_api_work_queue = queue.Queue()

# Processing lock to prevent reentrant calls
blender_api_processing_lock = threading.Lock()


def log(message: str, level: str = 'INFO'):
  """
  Thread-safe logging function.
  
  Args:
    message: The message to log
    level: Log level ('INFO', 'WARNING', 'ERROR')
  """
  if config.DEBUG or level in ('WARNING', 'ERROR'):
    print(f"[MCP-Link] [{level}] {message}")


def _process_blender_api_work_queue():
  """
  Process queued Blender API work - called from Blender's main thread via timer.
  
  This is the ONLY place where Blender API calls happen from MCP.
  Called every 0.1 seconds by Blender's timer system.
  
  Returns:
    Float: Time until next call (0.1 seconds)
  """
  # Try to acquire lock - if already processing, skip this call
  if not blender_api_processing_lock.acquire(blocking=False):
    return 0.1
  
  try:
    # Process up to 5 items per timer tick to avoid blocking Blender
    max_per_batch = 5
    processed = 0
    
    while processed < max_per_batch:
      try:
        work_item = blender_api_work_queue.get_nowait()
      except queue.Empty:
        break
      
      call_data = work_item['call_data']
      result_queue = work_item['result_queue']
      
      try:
        # Execute the actual work on main thread
        result = _handle_tool_call_on_main_thread(call_data)
      except Exception as e:
        error_trace = traceback.format_exc()
        log(f"ERROR during processing: {e}", 'ERROR')
        log(error_trace, 'ERROR')
        result = {
          "content": [{
            "type": "text",
            "text": f"FATAL ERROR in work queue processor:\n{error_trace}"
          }],
          "isError": True
        }
      
      # Return result to waiting thread
      result_queue.put(result)
      processed += 1
  
  finally:
    blender_api_processing_lock.release()
  
  return 0.1  # Call again in 0.1 seconds


def _create_mcp_client() -> MCPClient:
  """
  Create and configure the MCP client instance.
  
  Returns:
    Configured MCPClient instance ready to connect
  """
  tool_name = config.TOOL_NAME
  
  tool_readme = """Blender 3D - Use this to perform 3D modeling, animation, rendering, VFX, and more.
- Use this when you need to create, modify, or render 3D content
- Full access to Blender's Python API (bpy.ops, bpy.data, bpy.context)
- Can execute arbitrary Python code with complete Blender environment access
- Supports persistent Python sessions for complex multi-step workflows"""

  tool_description = """
Blender MCP Tool - UNLIMITED API Access + Python Execution + MCP Integration

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

  def tool_handler(call_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    THREAD-SAFE PROXY for Blender API calls.
    
    This function can be called from ANY thread. If called from a daemon thread,
    it queues the work and waits for the main thread to process it.
    """
    # Queue the work for main thread processing
    result_queue = queue.Queue()
    
    work_item = {
      'call_data': call_data,
      'result_queue': result_queue
    }
    
    blender_api_work_queue.put(work_item)
    
    # Wait for main thread to process it (blocks until result arrives)
    result = result_queue.get(timeout=120)  # 2 minute timeout
    
    return result
  
  def log_callback(message: str):
    """Log callback for MCP client."""
    log(f"[Client] {message}")
  
  return MCPClient(
    tool_name=tool_name,
    tool_description=tool_description,
    tool_readme=tool_readme,
    tool_handler=tool_handler,
    log_callback=log_callback
  )


def _handle_tool_call_on_main_thread(call_data: Dict[str, Any]) -> Dict[str, Any]:
  """
  ACTUAL implementation - MUST run on Blender's main thread.
  
  Routes to the appropriate handler based on operation type.
  """
  try:
    # Extract command parameters
    params = call_data.get('params', {})
    arguments = params.get('arguments', {})
    
    # Get operation type
    operation = arguments.get('operation', 'execute_python')  # Default to Python execution
    
    # Route to appropriate handler
    if operation == 'execute_python':
      return _handle_python_execution(arguments)
    elif operation == 'api_call':
      return _handle_api_call(arguments)
    elif operation == 'call_tool':
      return _handle_mcp_tool_call(arguments)
    else:
      # If no operation specified but there's code, treat as Python execution
      if 'code' in arguments:
        return _handle_python_execution(arguments)
      # Otherwise try API call style
      elif 'api_path' in arguments:
        return _handle_api_call(arguments)
      else:
        return {
          "content": [{"type": "text", "text": f"ERROR: Unknown operation '{operation}'. Use 'execute_python', 'api_call', or 'call_tool'."}],
          "isError": True
        }
  
  except Exception as e:
    error_trace = traceback.format_exc()
    log(f"ERROR in tool handler: {e}", 'ERROR')
    return {
      "content": [{"type": "text", "text": f"ERROR: {str(e)}\n\n{error_trace}"}],
      "isError": True
    }


def _handle_python_execution(arguments: Dict[str, Any]) -> Dict[str, Any]:
  """
  Execute arbitrary Python code with MAXIMUM access to Blender.
  
  Uses TRUE INLINE EXECUTION via exec(compile(code, "<ai-code>", "exec"), globals()).
  """
  import io
  import contextlib
  
  code = arguments.get('code')
  if not code:
    return {
      "content": [{"type": "text", "text": "ERROR: 'code' parameter required for execute_python operation"}],
      "isError": True
    }
  
  session_id = arguments.get('session_id', 'default')
  persistent = arguments.get('persistent', True)
  
  # Capture stdout and stderr
  stdout_capture = io.StringIO()
  stderr_capture = io.StringIO()
  
  try:
    # Create execution namespace with Blender access
    exec_namespace = {
      'bpy': bpy,
      'mathutils': __import__('mathutils'),
      'mcp': _create_mcp_bridge(),
      '__name__': '__main__',
      '__file__': '<ai-code>',
    }
    
    # If persistent session, restore previous session variables
    if persistent and session_id in python_sessions:
      exec_namespace.update(python_sessions[session_id])
    
    # Execute with captured output
    with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
      exec(compile(code, "<ai-code>", "exec"), exec_namespace)
    
    # Save session state if persistent (exclude built-ins and modules)
    if persistent:
      saved_vars = {}
      for key, value in exec_namespace.items():
        if (not key.startswith('_') and 
            key not in ['bpy', 'mathutils', 'mcp'] and
            not callable(value) and
            not isinstance(value, type) and
            not hasattr(value, '__module__')):
          try:
            # Only save serializable types
            saved_vars[key] = value
          except:
            pass
      python_sessions[session_id] = saved_vars
    
    # Extract return value if AI set __return__
    return_value = exec_namespace.get('__return__', None)
    
    stdout_text = stdout_capture.getvalue()
    stderr_text = stderr_capture.getvalue()
    
    result_data = {
      "success": True,
      "stdout": stdout_text,
      "stderr": stderr_text,
    }
    
    if return_value is not None:
      result_data["return_value"] = str(return_value)
    
    if persistent:
      result_data["session_id"] = session_id
      result_data["session_variables"] = list(python_sessions.get(session_id, {}).keys())
    
    return {
      "content": [{"type": "text", "text": json.dumps(result_data, indent=2)}],
      "isError": False
    }
    
  except Exception as e:
    error_trace = traceback.format_exc()
    
    result_data = {
      "success": False,
      "stdout": stdout_capture.getvalue(),
      "stderr": stderr_capture.getvalue(),
      "error": str(e),
      "traceback": error_trace
    }
    
    return {
      "content": [{"type": "text", "text": json.dumps(result_data, indent=2)}],
      "isError": True
    }


def _handle_api_call(arguments: Dict[str, Any]) -> Dict[str, Any]:
  """
  Handle direct API calls via path navigation.
  
  Example:
    {"api_path": "bpy.ops.mesh.primitive_cube_add", "kwargs": {"size": 2}}
  """
  api_path = arguments.get('api_path', '')
  args = arguments.get('args', [])
  kwargs = arguments.get('kwargs', {})
  
  if not api_path:
    return {
      "content": [{"type": "text", "text": "ERROR: 'api_path' required for api_call operation"}],
      "isError": True
    }
  
  try:
    # Navigate the path to get the target
    parts = api_path.split('.')
    
    # Start with bpy or the first module
    if parts[0] == 'bpy':
      target = bpy
      parts = parts[1:]
    else:
      return {
        "content": [{"type": "text", "text": f"ERROR: api_path must start with 'bpy.', got '{api_path}'"}],
        "isError": True
      }
    
    # Navigate down the path
    for part in parts:
      target = getattr(target, part)
    
    # Call if callable, otherwise just return value
    if callable(target):
      result = target(*args, **kwargs)
    else:
      result = target
    
    # Format result
    if result is None:
      result_text = "Operation completed successfully (returned None)"
    elif hasattr(result, 'name'):
      result_text = f"Result: {type(result).__name__}(name='{result.name}')"
    else:
      result_text = f"Result: {result}"
    
    return {
      "content": [{"type": "text", "text": result_text}],
      "isError": False
    }
    
  except Exception as e:
    error_trace = traceback.format_exc()
    return {
      "content": [{"type": "text", "text": f"ERROR calling {api_path}: {str(e)}\n\n{error_trace}"}],
      "isError": True
    }


def _handle_mcp_tool_call(arguments: Dict[str, Any]) -> Dict[str, Any]:
  """
  Call another MCP tool from Blender.
  """
  global mcp_client_instance
  
  tool_name = arguments.get('tool_name')
  tool_arguments = arguments.get('arguments', {})
  
  if not tool_name:
    return {
      "content": [{"type": "text", "text": "ERROR: 'tool_name' required for call_tool operation"}],
      "isError": True
    }
  
  if not mcp_client_instance or not mcp_client_instance.is_connected:
    return {
      "content": [{"type": "text", "text": "ERROR: MCP client not connected"}],
      "isError": True
    }
  
  try:
    result = mcp_client_instance.call_mcp_tool(tool_name, tool_arguments)
    return {
      "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
      "isError": False
    }
  except Exception as e:
    return {
      "content": [{"type": "text", "text": f"ERROR calling MCP tool '{tool_name}': {str(e)}"}],
      "isError": True
    }


class MCPBridge:
  """
  Bridge for calling other MCP tools from within Python code.
  
  Available as `mcp` in the execution namespace.
  """
  
  def call(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Call another MCP tool.
    
    Args:
      tool_name: Name of the tool (e.g., "sqlite", "browser", "user")
      arguments: Arguments to pass to the tool
      
    Returns:
      Tool response dictionary
      
    Example:
      mcp.call("sqlite", {"input": {"sql": ".tables", "tool_unlock_token": "29e63eb5"}})
    """
    global mcp_client_instance
    
    if not mcp_client_instance or not mcp_client_instance.is_connected:
      raise RuntimeError("MCP client not connected")
    
    return mcp_client_instance.call_mcp_tool(tool_name, arguments)


def _create_mcp_bridge() -> MCPBridge:
  """Create an MCP bridge instance for Python execution."""
  return MCPBridge()


def _auto_connect():
  """
  Automatically connect to MCP server.
  Called during startup if MCP_AUTO_CONNECT is True.
  """
  global mcp_client_instance
  
  if mcp_client_instance and mcp_client_instance.is_connected:
    log("Already connected to MCP server")
    return
  
  log("Starting auto-connect to MCP server...")
  
  mcp_client_instance = _create_mcp_client()
  success = mcp_client_instance.connect()
  
  if success:
    log("[SUCCESS] Auto-connected to MCP server!", 'INFO')
  else:
    log("Auto-connect failed - check logs for details", 'WARNING')


def start():
  """
  Initialize MCP integration when extension loads.
  
  Called from __init__.py register() function.
  """
  log("MCP Integration starting...")
  
  # Register the timer for processing work queue
  if not bpy.app.timers.is_registered(_process_blender_api_work_queue):
    bpy.app.timers.register(_process_blender_api_work_queue, first_interval=0.5)
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
  """
  Cleanup when extension unloads.
  
  Called from __init__.py unregister() function.
  """
  global mcp_client_instance
  
  log("MCP Integration stopping...")
  
  # Unregister the timer
  if bpy.app.timers.is_registered(_process_blender_api_work_queue):
    bpy.app.timers.unregister(_process_blender_api_work_queue)
    log("Unregistered work queue processor timer")
  
  # Disconnect MCP client
  if mcp_client_instance:
    if mcp_client_instance.is_connected:
      mcp_client_instance.disconnect()
    mcp_client_instance = None
  
  log("MCP Integration stopped")
