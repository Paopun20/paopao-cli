![PaoPao Logo](https://raw.githubusercontent.com/Paopun20/paopao-cli/main/docs/ppc_icon.png)

# 🥭 PaoPao's CLI Framework

A **powerful, secure, and extensible Command Line Interface (CLI) framework** designed to revolutionize your terminal workflow. Built with Python, it offers advanced plugin management, security features, and a rich user experience.

[![Python 3.6+](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/Apache-2.0)

---

## ⚡ Core Features

### 🛠️ **Built-in Commands**
| Command | Description | Enhanced Features |
|---------|-------------|-------------------|
| `install` | Install community commands | Security validation, branch selection, force overwrite |
| `uninstall` | Remove commands | Interactive confirmation, metadata cleanup |
| `list` | Show installed commands | Advanced filtering, sorting, detailed view |
| `update` | Update commands from Git | Change detection, force update option |
| `info` | Show command details | Complete metadata, dependency info |
| `search` | Find commands | Search by name, description, author |
| `test` | Test local commands | Security validation, timeout control |
| `doctor` | System health check | Comprehensive diagnostics, verbose mode |
| `repl` | experiment featerimental feature, interactive shell | Interactive Python shell for command development and testing |

### 🌍 **Community Integration**
- **Git repository support** (GitHub, GitLab, Bitbucket, Codeberg)
- **Automatic metadata extraction** from project files
- **Dependency management** and validation
- **Version tracking** with installation history
- **Shallow cloning** for faster installations

### 🔒 **Security Features**
- **URL scheme validation** (prevents local file access)
- **Suspicious pattern detection** in repositories
- **Code analysis** for potentially dangerous imports
- **User confirmation** for risky operations
- **File size limits** (10MB max per file)

---

## 🥭 Installation

### Quick Install
```bash
pip install paopao-cli
```

### Development Install
```bash
git clone https://github.com/Paopun20/paopao-cli.git
cd paopao-cli
pip install -e .
```

### Requirements
- **Python 3.6+**
- **Git** (for community commands)
- **Rich** (for enhanced terminal output)
- **rich-argparse** (for beautiful help pages)

---

## 🚀 Quick Start

### Basic Usage
```bash
# Show all available commands
ppc

# Get detailed help
ppc --help

# Check system health
ppc doctor
```

### Installing Community Commands
```bash
# Install from GitHub
ppc install https://github.com/user/awesome-command

# Install specific branch
ppc install https://github.com/user/command --branch develop

# Install with custom name
ppc install https://github.com/user/tool --name mytool

# Force overwrite existing command
ppc install https://github.com/user/command --force
```

### Managing Commands
```bash
# List all commands with details
ppc list --detailed

# List only community commands
ppc list --source community

# Sort by installation date
ppc list --sort installed --reverse

# Search for commands
ppc search "git"
ppc search "deploy" --source community

# Show detailed command info
ppc info my-command

# Update a command
ppc update my-command

# Uninstall with confirmation
ppc uninstall old-command
```

### Development & Testing
```bash
# Test a local command script
ppc test --file my_script.py

# Test with security validation
ppc test --file script.py --validate --timeout 60

# Test with arguments
ppc test --file deploy.py -- --env production --dry-run
```

---

## 📁 Project Structure

```
paopao-cli/
├── ppc_commands/          # Official commands
├── ppc_addon/            # Community commands
├── .ppc_cache/           # Cache and metadata
├── docs/                 # Documentation
└── main.py              # Core framework
```

### Command Structure
# Addon Structure 0.0.1.1dev8+ (can add multiple commands per repository)
```
my-command/
├── commands/
│   ├── command_name.py
│   ├── another_command.py
│   └── ...
├── ppc.project.json     # Project metadata (legacy)
├── ppc.project.toml     # Project metadata (0.0.1.dev10+)
├── requirements.txt     # Dependencies (optional)
└── README.md           # Documentation (optional)
```

# Legacy Structure (can add only one command per repository)
```
my-command/
├── main.py              # Entry point (required)
├── ppc.project.json     # Project metadata (legacy)
├── ppc.project.toml     # Project metadata (0.0.1.dev10+)
├── requirements.txt     # Dependencies (optional)
└── README.md           # Documentation (optional)
```

---

## 🔧 Advanced Configuration

### Project Metadata (`ppc.project.toml`) (0.0.1.dev10+)
```toml
[project]
name = "plugin-name"
version = "0.1.0"
description = "Description plugin"
author = "Developer name"
python_version = ">=3.9"
dependencies = ["rich", "requests"]
```

### Project Metadata (`ppc.project.json`) (legacy)
```json
{
  "name": "plugin-name",
  "version": "0.1.0",
  "author": "Developer name",
  "description": "Description plugin",
  "python_version": ">=3.9",
  "dependencies": ["rich", "requests"],
  "keywords": ["automation", "productivity"],
  "homepage": "https://github.com/user/plugin-name"
}
```

---

## 🛡️ Security Guidelines

### For Users
- **Review code** before installing community commands
- **Use trusted sources** (GitHub, GitLab, etc.)
- **Enable validation** with `--validate` flag during testing
- **Regular updates** keep commands secure

### For Developers
- **Minimize dependencies** in your commands
- **Avoid dangerous imports** (subprocess, eval, etc.)
- **Include metadata** in `ppc.project.json`
- **Document security implications** in your README

---

## 🔍 Troubleshooting

### Common Issues

**Command not found after installation?**
```bash
# Refresh command cache
ppc doctor
# Or force cache refresh
ppc list --detailed
```

**Installation timeout?**
```bash
# Increase timeout for large repositories
ppc install https://github.com/large/repo --no-shallow
```

**Permission errors?**
```bash
# Check directory permissions
ppc doctor --verbose
```

**Git errors?**
```bash
# Verify git installation
git --version # Should return git version if not installed, go to https://git-scm.com/downloads for installation
# or
pip show GitPython # Should return GitPython package info if not installed, run pip install GitPython

# Check network connectivity
ppc install https://github.com/test/repo
```

### System Health Check
```bash
# Comprehensive system check
ppc doctor --verbose

# Check specific components
ppc doctor  # Basic check
```

---

## 🤝 Contributing

### Creating Commands
This is a simple template to create your own command compatible with PaoPao's CLI.
AND THIS REPO IS OPEN SOURCE, YOU CAN CONTRIBUTE YOUR COMMANDS TO THE COMMUNITY! BUT UNDER APACHE LICENSE 2.0

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 💬 Support

- 🐛 **Issues**: [GitHub Issues](https://github.com/Paopun20/paopao-cli/issues)