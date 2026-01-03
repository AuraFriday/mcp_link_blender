# Contributing to MCP-Link for Blender

Thank you for your interest in contributing to MCP-Link for Blender! We welcome contributions from the community.

## How to Contribute

### Reporting Bugs

1. Check the [existing issues](https://github.com/AuraFriday/mcp_link_blender/issues) to see if the bug has already been reported
2. If not, [open a new issue](https://github.com/AuraFriday/mcp_link_blender/issues/new) with:
   - A clear, descriptive title
   - Steps to reproduce the bug
   - Expected vs actual behavior
   - Your Blender version and operating system
   - Any relevant error messages from Blender's System Console

### Suggesting Features

1. [Open a new issue](https://github.com/AuraFriday/mcp_link_blender/issues/new) with the "enhancement" label
2. Describe the feature and why it would be useful
3. Include any relevant examples or mockups

### Submitting Code

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/mcp_link_blender.git
   cd MCP-Link-Blender
   ```
3. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/my-new-feature
   ```
4. **Make your changes** with clear, descriptive commits
5. **Test your changes** in Blender
6. **Push to your fork**:
   ```bash
   git push origin feature/my-new-feature
   ```
7. **Open a Pull Request** against the `main` branch

### Code Style

- Follow PEP 8 for Python code
- Use descriptive variable and function names
- Add comments for complex logic
- Keep functions focused and modular

### Testing

Before submitting:

1. Install your modified extension in Blender
2. Verify the MCP connection works
3. Test basic operations (Python execution, API calls)
4. Check Blender's System Console for errors

## Development Setup

```bash
# Clone the repository
git clone https://github.com/AuraFriday/mcp_link_blender.git
cd MCP-Link-Blender

# Build the extension
make build

# Install to Blender for testing
make install
```

## License

By contributing to MCP-Link for Blender, you agree that your contributions will be licensed under the GPL-3.0-or-later license.

## Questions?

Feel free to [open an issue](https://github.com/AuraFriday/mcp_link_blender/issues) or contact us at ask@aurafriday.com.

Thank you for helping improve MCP-Link for Blender!
