# MCP-Link for Blender
# ====================
# Connect AI agents to Blender via Model Context Protocol (MCP)
#
# This extension enables AI agents (Claude, ChatGPT, Cursor, etc.) to control
# Blender through natural language by exposing the entire Blender Python API.
#
# Copyright (c) 2025 Christopher Nathan Drake / Aura Friday
# License: GPL-3.0-or-later

bl_info = {
  "name": "MCP-Link for Blender",
  "author": "Christopher Nathan Drake",
  "version": (1 , 0 , 0),
  "blender": (4, 2, 0),
  "location": "System",
  "description": "Connect AI agents to Blender via Model Context Protocol (MCP)",
  "warning": "Gives AI full access to Blender - use responsibly!",
  "doc_url": "https://aurafriday.com/mcp-link",
  "category": "Development",
}


def register():
  """Called when the extension is enabled."""
  from . import mcp_integration
  
  print("=" * 60)
  print("MCP-Link for Blender: Starting...")
  print("=" * 60)
  
  try:
    mcp_integration.start()
    print("[OK] MCP-Link extension loaded successfully")
  except Exception as e:
    print(f"[ERROR] Failed to start MCP-Link: {e}")
    import traceback
    traceback.print_exc()


def unregister():
  """Called when the extension is disabled."""
  from . import mcp_integration
  
  print("=" * 60)
  print("MCP-Link for Blender: Stopping...")
  print("=" * 60)
  
  try:
    mcp_integration.stop()
    print("[OK] MCP-Link extension unloaded successfully")
  except Exception as e:
    print(f"[ERROR] Failed to stop MCP-Link cleanly: {e}")
    import traceback
    traceback.print_exc()


if __name__ == "__main__":
  register()
