# Privacy Policy for MCP-Link for Blender

**Last Updated:** 2025-01-03

Welcome to MCP-Link for Blender. Your privacy is not an afterthought; it is a core principle of our architecture. This policy explains what data we process and, more importantly, what we **do not**.

Our guiding principle is simple: **we collect the absolute minimum data necessary to provide our service, and in most cases, that means we collect nothing at all.**

### 1. The "Zero-Collection" Principle

For the core functionality of the MCP-Link for Blender extension:

*   **We DO NOT collect or store any personal data.**
*   **We DO NOT use any third-party analytics, metrics, or telemetry services.**
*   **We DO NOT track your tool usage or interactions with AI agents.**

The extension is designed to operate on your local machine, under your complete control. Any data processed by the extension, AI interactions, or Blender operations remains on your local machine. This data is never sent to, seen by, or stored by Aura Friday.

### 2. Data Processing You Control

The MCP-Link for Blender extension, by its nature, interacts with data to function. This processing happens under your explicit control:

*   **Blender Operations:** The extension executes Blender Python API commands when instructed by AI agents through the MCP protocol.
*   **File Operations:** The extension may read, write, or modify files (such as renders, blend files, or exports) when instructed by AI agents.
*   **Network Requests:** The extension communicates with the local MCP-Link server running on your machine. No external network requests are made by the extension itself.

All data processing is entirely local to your machine unless you explicitly configure external integrations through the MCP-Link server.

### 3. MCP-Link Server Communication

The extension connects to a locally-running MCP-Link server via Server-Sent Events (SSE). This communication:

*   Happens entirely on your local machine (localhost)
*   Uses encrypted connections (HTTPS) even locally
*   Does not transmit data to any external servers

### 4. Your Rights (GDPR & Global Privacy Standards)

Since we do not collect any personal data through this extension, there is nothing to access, rectify, or delete. However, we respect your rights over your data. If you have any concerns, please contact us at the email address below.

### 5. Data Security

The extension implements industry-standard security measures:

*   All communication with the MCP-Link server uses TLS encryption
*   No credentials or sensitive data are stored by the extension
*   All operations require explicit AI agent commands

### 6. Children's Privacy

Our software is not directed to individuals classified as children. We do not knowingly collect personal data from anyone, including children.

### 7. Changes to This Policy

We may update this Privacy Policy from time to time. We will notify you of any significant changes by updating this file in the repository.

### 8. Contact Us

If you have any questions about this Privacy Policy, please contact:

**Aura Friday**  
an Australian proprietary limited company  
Email: `privacy@aurafriday.com`  
Address: PO Box 988, Noosa Heads, QLD 4567, Australia
