
![PaoPao Logo](./docs/ppc_icon.png)

# 🥭 PaoPao CLI Framework
A versatile and **user-friendly Command Line Interface (CLI) framework** designed to simplify your terminal workflow.
It comes with **built-in commands**, **community plugins**, and **extensible architecture**, perfect for both beginners and advanced users.

---

## ⚡ Features
- 🛠️ Built-in commands: install, uninstall, list, update, test  
- 🌍 Community commands: easily install and manage third-party CLI extensions  
- 🐍 Python-based: lightweight and extensible  
- 📦 Plugin architecture: add new commands without touching core code  
- 🧪 Test local commands before publishing  
- 🔄 Update installed commands from Git repositories  
- 📝 Rich terminal output using **Rich** library (tables, panels, colors)

---

## 🥭 Installation
Install the latest version directly from GitHub:

pip install git+https://github.com/paoun20/paopao-command.git

---

## 🚀 Usage
Run commands using the `ppc` CLI:

ppc <command> [options]

### Examples
- Install a community command:  
```bash
ppc install https://github.com/user/my-command
```
- List installed community commands:  
```bash
ppc list
```
- Test a local command script:  
```bash
ppc test --file main.py -- arg1 arg2
```
- Update a command from its Git repository:  
```bash
ppc update my-command
```

---

## 💡 Tips
- Use `ppc` without arguments to see **all available commands**  
- Community commands override official ones if they share the same name  
- Emoji icons help quickly identify command types:  
  - 🛠️ Official commands  
  - 🌍 Community commands  
  - 📥 Install / 🗑️ Uninstall / 🔄 Update / 🧪 Test  
