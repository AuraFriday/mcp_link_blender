# MCP-Link for Blender - Build System
# =====================================
#
# USAGE: Run from WSL (preferred) or Windows cmd.exe with GNU Make
#
# Prerequisites:
#   - WSL: make (apt install make)
#   - Windows: GNU Make for Windows
#   - Blender 4.2+ installed (for extension building)
#
# Commands:
#   make          - Build the extension zip
#   make build    - Same as above
#   make install  - Build and install to Blender
#   make clean    - Remove build artifacts
#   make version  - Show current version
#   make bump-patch - Bump patch version (1.0.0 -> 1.0.1)
#   make bump-minor - Bump minor version (1.0.0 -> 1.1.0)
#   make bump-major - Bump major version (1.0.0 -> 2.0.0)

# Configuration
EXTENSION_NAME := mcp_link_blender
VERSION_FILE := version.txt
VERSION := $(shell cat $(VERSION_FILE) 2>/dev/null || echo "1.0.0")
OUTPUT_DIR := dist
SOURCE_DIR := $(EXTENSION_NAME)
ZIP_NAME := $(EXTENSION_NAME)-$(VERSION).zip

# Detect OS for Blender path
ifeq ($(OS),Windows_NT)
    # Running in Windows (cmd.exe or PowerShell with GNU Make)
    BLENDER := "C:/Program Files/Blender Foundation/Blender 5.0/blender.exe"
    BLENDER_EXTENSIONS := $(APPDATA)/Blender Foundation/Blender/5.0/extensions/user_default
    MKDIR := mkdir
    RM := del /Q
    RMDIR := rmdir /S /Q
    CP := copy
    SEP := \\
else
    # Running in WSL or Linux
    BLENDER := "/mnt/c/Program Files/Blender Foundation/Blender 5.0/blender.exe"
    BLENDER_EXTENSIONS := $(HOME)/.config/blender/5.0/extensions/user_default
    # For WSL accessing Windows Blender user data:
    BLENDER_EXTENSIONS_WIN := /mnt/c/Users/$(shell cmd.exe /c "echo %USERNAME%" 2>/dev/null | tr -d '\r')/AppData/Roaming/Blender\ Foundation/Blender/5.0/extensions/user_default
    MKDIR := mkdir -p
    RM := rm -f
    RMDIR := rm -rf
    CP := cp
    SEP := /
endif

# Files to update with version
VERSION_FILES := $(SOURCE_DIR)/blender_manifest.toml $(SOURCE_DIR)/__init__.py

.PHONY: all build install clean version bump-patch bump-minor bump-major update-version help

# Default target
all: build

help:
	@echo "MCP-Link for Blender - Build System"
	@echo "===================================="
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  build        - Build the extension zip (default)"
	@echo "  install      - Build and install to Blender"
	@echo "  clean        - Remove build artifacts"
	@echo "  version      - Show current version"
	@echo "  bump-patch   - Bump patch version (1.0.0 -> 1.0.1)"
	@echo "  bump-minor   - Bump minor version (1.0.0 -> 1.1.0)"
	@echo "  bump-major   - Bump major version (1.0.0 -> 2.0.0)"
	@echo ""
	@echo "Current version: $(VERSION)"

version:
	@echo "$(VERSION)"

# Update version in all relevant files
update-version:
	@echo "Updating version to $(VERSION) in all files..."
	@# Update blender_manifest.toml
	@sed -i 's/^version = ".*"/version = "$(VERSION)"/' $(SOURCE_DIR)/blender_manifest.toml
	@# Update __init__.py - the version tuple
	@sed -i 's/"version": ([0-9]*, [0-9]*, [0-9]*)/"version": ($(subst ., $(comma) ,$(VERSION)))/' $(SOURCE_DIR)/__init__.py || true
	@# Alternative format for bl_info version
	@python3 -c "import re; \
		v = '$(VERSION)'.split('.'); \
		content = open('$(SOURCE_DIR)/__init__.py').read(); \
		content = re.sub(r'\"version\": \([0-9]+, [0-9]+, [0-9]+\)', f'\"version\": ({v[0]}, {v[1]}, {v[2]})', content); \
		open('$(SOURCE_DIR)/__init__.py', 'w').write(content)" 2>/dev/null || \
		echo "Note: Python3 not available for __init__.py update, please update manually"
	@echo "Version updated to $(VERSION)"

# Build the extension zip
build: update-version
	@echo "Building $(ZIP_NAME)..."
	@$(MKDIR) $(OUTPUT_DIR) 2>/dev/null || true
	@# Create zip file (using Python for cross-platform compatibility)
	@python3 -c "import shutil, os; \
		os.makedirs('$(OUTPUT_DIR)', exist_ok=True); \
		shutil.make_archive('$(OUTPUT_DIR)/$(EXTENSION_NAME)-$(VERSION)', 'zip', '.', '$(SOURCE_DIR)')" 2>/dev/null || \
		(cd $(SOURCE_DIR) && zip -r ../$(OUTPUT_DIR)/$(ZIP_NAME) . -x '*.pyc' -x '__pycache__/*' -x '.git/*')
	@echo ""
	@echo "Build complete: $(OUTPUT_DIR)/$(ZIP_NAME)"
	@echo ""
	@ls -lh $(OUTPUT_DIR)/$(ZIP_NAME) 2>/dev/null || dir $(OUTPUT_DIR)$(SEP)$(ZIP_NAME)

# Install to Blender (WSL version - uses Windows Blender)
install: build
	@echo "Installing to Blender..."
ifeq ($(OS),Windows_NT)
	@$(BLENDER) --command extension install-file -r user_default -e "$(OUTPUT_DIR)/$(ZIP_NAME)"
else
	@# WSL: Use Windows path for Blender command
	@$(BLENDER) --command extension install-file -r user_default -e "$$(wslpath -w $(OUTPUT_DIR)/$(ZIP_NAME))"
endif
	@echo "Installation complete!"
	@echo "Restart Blender to load the extension."

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	@$(RMDIR) $(OUTPUT_DIR) 2>/dev/null || true
	@$(RM) *.zip 2>/dev/null || true
	@find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name '*.pyc' -delete 2>/dev/null || true
	@echo "Clean complete."

# Version bumping
bump-patch:
	@echo "Current version: $(VERSION)"
	@python3 -c "v='$(VERSION)'.split('.'); v[2]=str(int(v[2])+1); print('.'.join(v))" > $(VERSION_FILE)
	@echo "New version: $$(cat $(VERSION_FILE))"
	@$(MAKE) update-version VERSION=$$(cat $(VERSION_FILE))

bump-minor:
	@echo "Current version: $(VERSION)"
	@python3 -c "v='$(VERSION)'.split('.'); v[1]=str(int(v[1])+1); v[2]='0'; print('.'.join(v))" > $(VERSION_FILE)
	@echo "New version: $$(cat $(VERSION_FILE))"
	@$(MAKE) update-version VERSION=$$(cat $(VERSION_FILE))

bump-major:
	@echo "Current version: $(VERSION)"
	@python3 -c "v='$(VERSION)'.split('.'); v[0]=str(int(v[0])+1); v[1]='0'; v[2]='0'; print('.'.join(v))" > $(VERSION_FILE)
	@echo "New version: $$(cat $(VERSION_FILE))"
	@$(MAKE) update-version VERSION=$$(cat $(VERSION_FILE))

# Helper for comma in subst
comma := ,
