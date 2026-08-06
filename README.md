# 🍲 skill-guabao — A Skill Plugin Manager for AI Agents

[繁體中文版說明 (Traditional Chinese)](README-zh.md)

**GuaBao** (刈包 - meaning Taiwanese pork belly bun) is a lightweight plugin manager for Google Antigravity Skills. Just like the traditional street food that wraps various delicious fillings into one bun, GuaBao helps you securely wrap, manage, and track all your AI Agent plugins!

It provides a lifecycle management system for plugins and utilizes the GitHub API to automatically determine whether third-party skills have a stable new version available for an update. It natively protects against file conflicts, rogue updates, and untested bleeding-edge code.

---

## 🤔 Why use GuaBao?

As you use AI Agents, you might find yourself installing more and more plugins (Skills), or even modifying third-party plugins to suit your specific needs. This leads to several pain points:
1. **Accidental Overwrites**: When you ask an AI to "update a plugin," it might blindly overwrite the entire directory, wiping out your hard-earned local customizations!
2. **Tracking Chaos**: It's hard to keep track of what plugins are installed, which ones you wrote, and which ones are from third parties.
3. **Bleeding-Edge Instability**: The latest commit on a GitHub repo isn't always stable. Blindly running `git pull` can easily break your working environment.
4. **Untrusted Sources**: AI agents might hallucinate or pull code from unknown, untrusted repositories.

**GuaBao solves these problems:**
Acting as a "manager" for your Agent, GuaBao sits between the AI and your system. It provides conflict protection (Diff Scans), an update maturity check (3-day observation period), idle plugin tracking, and a trusted hosts whitelist. This allows your AI assistant to freely and securely manage your development environment without you having to worry about it breaking things!

---

## 🛡️ Key Features

- **Automated Update Checking**: Identifies stable updates for your third-party skills using a 3-day maturity check to avoid unstable bleeding-edge commits.
- **Diff Scan Protection**: Before applying updates, GuaBao uses GitHub Tree APIs and local Git Blob SHA1 calculations to scan for any local modifications. If you've customized a third-party plugin, GuaBao immediately halts the update to prevent overwriting your hard work.
- **Naming Conflict Prevention**: Safely manages namespaces and prevents accidental overwriting of existing skills during new installations.
- **Archive & Rollback**: Safe uninstallation process that archives deleted plugins to `~/.gemini/config/archive/` instead of executing a permanent wipe.
- **Idle Plugin Tracking**: Automatically tracks usage and marks plugins as "idle" if they haven't been used in over 60 days.
- **Trusted Hosts Boundary**: Warns you if an AI agent tries to install a plugin from a source outside of your explicitly trusted GitHub organizations (e.g., `github.com/anthropics`).

---

## 📦 Installation

Installing `skill-guabao` is incredibly simple. You don't need to manually clone repositories or copy files. 

Just copy the link to this repository and paste it into your AI Agent's chat (e.g., Antigravity IDE) with a prompt like this:

> "Please help me install this plugin: https://github.com/YuJunWang/skill-guabao"

Your AI Agent will automatically handle the cloning, setup the `SKILL.md` instructions, and initialize the required configurations for you!

---

## 📁 Directory Structure

```
skill-guabao/
├── plugin.json                          # Plugin Metadata
├── plugins_inventory.template.yaml      # Inventory Template
├── skills/
│   └── skill-guabao/
│       └── SKILL.md                     # Agent Instructions for managing skills
└── scripts/
    ├── guabao_updater.py                # Core Updater Script
    └── test_guabao_updater.py           # Pytest Test Cases
```

## 🤖 AI Agent Trigger Guidelines

If you want your AI assistant (e.g. Antigravity Agent) to proactively use GuaBao to manage your plugins, it is recommended to add the following rules to your global configuration file (e.g., `AGENTS.md` or system prompt):

> **Plugin and Ecosystem Management**: When encountering a need to install a new plugin, write a new local utility skill (including in `config/plugins/` or `config/skills/`), or check if packages need an update, **you must proactively consult the `skill-guabao` skill** to confirm the global registry (`plugins_inventory.yaml`) specifications. After creating any new global skills, you must proactively register them into GuaBao's inventory for future tracking.

This ensures that whenever the AI detects you asking about plugin updates or preparing to create a new plugin, it will automatically engage GuaBao's management mechanisms.

---

## 🚀 Quick Start

### Step 1: Initialize Your Plugin Inventory

Copy the template to your Antigravity config directory:

**Windows:**
```powershell
Copy-Item .\plugins_inventory.template.yaml "$env:USERPROFILE\.gemini\config\plugins_inventory.yaml"
```

**macOS / Linux:**
```bash
cp plugins_inventory.template.yaml ~/.gemini/config/plugins_inventory.yaml
```

### Step 2: Edit Your Plugin List

Open `~/.gemini/config/plugins_inventory.yaml` and populate it with your installed plugins according to the four categories.

### Step 3: Run Update Checks

```bash
# Uses the default path (~/.gemini/config/plugins_inventory.yaml)
python scripts/guabao_updater.py

# Or specify a custom path
python scripts/guabao_updater.py --inventory /path/to/your/plugins_inventory.yaml

# Developer feature: Bump the last_updated date to today for a specific plugin (usually after pushing to GitHub)
python scripts/guabao_updater.py --bump <skill_name>
```

---

## 🗂️ The Four Plugin Categories

| Category | Use Case | AI Editable? | Update Method |
|:---:|---|:---:|---|
| `git_tracked_skills` | Open source plugins developed by you | ✅ Yes | Edit directly via Symlink, or use sync scripts for monorepos |
| `local_utility_skills` | Lightweight, local-only tools | ✅ Yes | Edit directly |
| `third_party_git_skills` | Open source plugins pulled from GitHub | 🔴 Prohibited | Archive old version and re-clone the latest version |
| `system_bundled_skills` | Core plugins bundled with the system | 🔴 Prohibited | Automatic with system updates |

---

## 🧪 Running Tests

```bash
cd scripts/
pytest test_guabao_updater.py -v
```

---

## ⚙️ Dependencies

- Python 3.8+
- `pyyaml`
- `requests`
- `pytest` (For testing)
