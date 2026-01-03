"""
File: config.py
Project: MCP-Link Blender Extension
Component: Configuration settings
Author: Christopher Nathan Drake (cnd)
Created: 2025-01-03
SPDX-License-Identifier: GPL-3.0-or-later
Copyright: (c) 2025 Christopher Nathan Drake. All rights reserved.
"""

# Enable debug logging
DEBUG = True

# Enable MCP-specific debug logging (very verbose)
MCP_DEBUG = False

# Auto-connect to MCP server on extension load
MCP_AUTO_CONNECT = True

# Tool name as it appears in MCP
TOOL_NAME = "blender"

# Reconnection settings
MAX_RETRY_DELAY = 60  # Maximum seconds between reconnection attempts
