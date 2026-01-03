"""
File: __init__.py
Project: MCP-Link Blender Extension
Component: Main entry point for the Blender extension
Author: Christopher Nathan Drake (cnd)
Created: 2025-01-03
SPDX-License-Identifier: GPL-3.0-or-later
Copyright: (c) 2025 Christopher Nathan Drake. All rights reserved.

MCP-Link for Blender - Connect AI agents to Blender via Model Context Protocol (MCP)

This extension enables AI agents (like Claude, ChatGPT, Cursor) to control Blender
through the Model Context Protocol. The AI gets full access to Blender's Python API,
can execute arbitrary Python code, and can integrate with other MCP tools.

For Blender 5.0+
"""

bl_info = {
  "name": "MCP-Link for Blender",
  "author": "Christopher Nathan Drake",
  "version": (1 , 0 , 0),
  "blender": (5, 0, 0),
  "location": "System",
  "description": "Connect AI agents to Blender via Model Context Protocol (MCP)",
  "warning": "Gives AI full access to Blender - use responsibly!",
  "doc_url": "https://aurafriday.com/mcp-link",
  "category": "Development",
}


def register():
  """
  Called when the extension is enabled.
  
  Starts the MCP integration which:
  1. Registers a work queue processor timer
  2. Auto-connects to the MCP-Link server
  3. Registers Blender as an MCP tool
  4. Listens for incoming AI commands
  """
  from . import mcp_integration
  
  print("="*60)
  print("MCP-Link for Blender: Starting...")
  print("="*60)
  
  try:
    mcp_integration.start()
    print("[OK] MCP-Link extension loaded successfully")
  except Exception as e:
    print(f"[ERROR] Failed to start MCP-Link: {e}")
    import traceback
    traceback.print_exc()


def unregister():
  """
  Called when the extension is disabled.
  
  Cleans up:
  1. Disconnects from MCP server
  2. Unregisters timers
  3. Cleans up resources
  """
  from . import mcp_integration
  
  print("="*60)
  print("MCP-Link for Blender: Stopping...")
  print("="*60)
  
  try:
    mcp_integration.stop()
    print("[OK] MCP-Link extension unloaded successfully")
  except Exception as e:
    print(f"[ERROR] Failed to stop MCP-Link cleanly: {e}")
    import traceback
    traceback.print_exc()


if __name__ == "__main__":
  register()
