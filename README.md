# TeddyCloudStarter

[![Publish to PyPI](https://github.com/Quentendo64/TeddyCloudStarter/actions/workflows/publish-to-pypi.yml/badge.svg)](https://github.com/Quentendo64/TeddyCloudStarter/actions)

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![PyPI version](https://badge.fury.io/py/teddycloudstarter.svg)](https://badge.fury.io/py/teddycloudstarter)
[![Python 3.6+](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)
![Status: Beta](https://img.shields.io/badge/status-beta-orange)

**A user-friendly wizard for setting up TeddyCloud deployments with Docker**

## 🌟 Overview

> **BETA RELEASE**: This project is fully functional but still in beta. It may contain bugs and is under active development. Please use with caution and report any issues on GitHub.

TeddyCloudStarter is a comprehensive wizard that simplifies the process of setting up and managing TeddyCloud deployments using Docker. It provides an interactive interface that guides users through configuration, deployment, security setup, and maintenance of their TeddyCloud instance.

## 🚀 Getting Started

### Prerequisites

- **Python 3.6+**
- **Docker** and **Docker Compose**
- **Internet connection** (for first-time setup and updates)

### Installation

<details>
<summary><b>📦 Using pip (Recommended)</b></summary>

```bash
pip install TeddyCloudStarter
```

</details>

<details>
<summary><b>🔧 From source</b></summary>

```bash
git clone https://github.com/Quentendo64/TeddyCloudStarter.git
cd TeddyCloudStarter
pip install -e .
```

</details>

## 💻 Usage

### Quick Start

Launch the wizard by running:

```bash
TeddyCloudStarter
```

This starts an interactive interface that guides you through the setup process step-by-step.

## ⚙️ Configuration

### Setup Options

| Feature | Description |
|---------|-------------|
| 🌐 **Language Selection** | Choose between English and German interfaces |
| 🔄 **Deployment Mode** | Select direct mode or Nginx reverse proxy mode |
| 📝 **Configuration Management** | Manage your TeddyCloud configuration |

## 🔒 Security

TeddyCloudStarter provides multiple security layers:

| Feature | Description |
|---------|-------------|
| 🔐 **Let's Encrypt Integration** | Automatic SSL certificate management |
| 🛡️ **Custom Certificate Authority** | Create and manage your own CA |
| 🔑 **Client Certificates** | Secure access with client certificate authentication |
| 👤 **Basic Authentication** | Simple username/password protection |
| 🌐 **IP Restrictions** | Control access by IP address |

## 🧰 Management Tools

| Feature | Description |
|---------|-------------|
| 🐳 **Docker Management** | Start, stop, and manage Docker containers and services |
| 📱 **Application Management** | Configure and manage TeddyCloud |
| 💾 **Backup & Recovery** | Create and restore backups of your configuration |
| 🔧 **Support Tools** | Access logs and troubleshooting utilities |


## 👏 Special Mentions

- [henryk](https://forum.revvox.de/u/henryk/) from Revoxx Forum - For extensive testing and heroic support during development


## 📄 License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.