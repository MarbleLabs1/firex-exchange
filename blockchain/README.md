# Brocus CLI

**Brocus CLI** is a revolutionary terminal enhancement system that integrates with your native shell across all platforms. It brings Warp-inspired AI suggestions, elegant themes, and powerful preview capabilities directly to your existing terminal.

![Brocus CLI Banner](docs/banner.png)

## Vision

Brocus CLI doesn't replace your terminal - it enhances it with an elegant overlay that adds powerful features while preserving your workflow:

- **Native Terminal Integration**: Works with PowerShell, CMD, Bash, Zsh, and more - enhances rather than replaces
- **ALLINONE Architecture**: A unified core with platform-specific adapters ensures consistent experiences everywhere
- **Python Native Core**: Importable as a library for blockchain, Android development, or any Python project
- **AI-Powered Suggestions**: Predicts your next command with context-aware intelligence
- **Dynamic Themes**: Transform your terminal's appearance with beautiful, customizable themes
- **Command Preview**: See what commands will do before running them
- **Plugin System**: Expandable with custom plugins for specific workflows

## Innovative Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    ALLINONE Core                         │
│  ┌───────────┐  ┌──────────┐  ┌──────────────────────┐  │
│  │ Theming   │  │   AI     │  │ Command Prediction   │  │
│  │ Engine    │  │ Suggest  │  │ & Preview Engine     │  │
│  └───────────┘  └──────────┘  └──────────────────────┘  │
└────────────┬─────────────┬─────────────┬────────────────┘
             │             │             │
┌────────────▼─────┐ ┌─────▼──────┐ ┌────▼────────────────┐
│ Windows Adapter  │ │ Linux/Mac  │ │ Android Terminal    │
│ ┌──────┐ ┌──────┐│ │ Adapter    │ │ Adapter             │
│ │PowerS│ │ CMD  ││ │            │ │                     │
│ │hell  │ │      ││ │            │ │                     │
│ └──────┘ └──────┘│ │            │ │                     │
└──────────────────┘ └────────────┘ └─────────────────────┘
```

## Features

- **Terminal Hooks**: Intercepts and enhances terminal I/O without disrupting the native experience
- **Transparent Overlay UI**: Adds features like command suggestions while keeping the native terminal visible
- **Theme Engine**: Changes colors, fonts, and UI elements of the actual terminal
- **AI Suggestion System**: Context-aware command completion based on history and current directory
- **Plugin API**: Extend functionality with custom plugins
- **Cross-Platform Sync**: Settings and preferences follow you across devices

## Installation

```bash
# Install the core package
pip install brocus-cli

# Install platform-specific adapter
brocus install-adapter

# Initialize and connect to your terminal
brocus init
```

## Usage

Brocus CLI runs in the background and enhances your terminal automatically. Special commands:

```bash
# View and change themes
brocus theme list
brocus theme apply monokai

# Manage AI suggestions
brocus ai enable
brocus ai configure

# Create custom plugins
brocus plugin create my-plugin
```

## For Developers

Brocus CLI is designed to be imported as a library:

```python
from brocus import terminal, themes, suggest

# Use in your Python applications
terminal.enhance()
suggest.get_command_predictions(context)
```

## Philosophy: ALLINONE

The shared core ensures that updates, features, and fixes are automatically available across all platforms. Write once, enhance everywhere.

---

**Contributions, issues, and feature requests are welcome!**
