# TeddyCloudStarter

[![Python 3.6+](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![License: GPL-3.0](https://img.shields.io/badge/License-GPL%203.0-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

A user-friendly wizard for setting up TeddyCloud deployments with Docker.

## ALPHA - RELEASE

WARNING - Very early development stage
Keep in mind that this project by far is not finished yet.
But it should bring you the concept of how it will work. 

Soon™ 

## 🌟 Features

- Interactive setup wizard with step-by-step configuration
- Docker deployment management with docker-compose
- SSL/TLS certificate generation and management
- Nginx configuration for edge and authentication servers
- Multi-language support (English, German)
- Configuration backup and restore
- Automatic updates checking

## 📋 Requirements

- Python 3.6 or newer
- Docker and Docker Compose
- Internet connection (for first-time setup and updates)

## 🚀 Installation

### Using pip

```bash
pip install TeddyCloudStarter
```

### From source

```bash
git clone https://github.com/Quentendo64/TeddyCloudStarter.git
cd TeddyCloudStarter
pip install -e .
```

## 💻 Usage

### Starting the wizard

```bash
TeddyCloudStarter
```

The wizard will guide you through the setup process with an interactive interface.

### Configuration Options

TeddyCloudStarter allows you to:
- Configure network settings
- Generate and manage SSL/TLS certificates
- Set up Docker containers
- Customize Nginx configurations
- Backup and restore your setup

## 🔧 Development

### Setting up the development environment

```bash
git clone https://github.com/Quentendo64/TeddyCloudStarter.git
cd TeddyCloudStarter
pip install -e ".[dev]"
```

### Running tests

```bash
pytest
```

### Compiling translations

```bash
python extract_translations.py
python compile_translations.py
```

## 📁 Project Structure

```
TeddyCloudStarter/
├── TeddyCloudStarter/        # Main package
│   ├── certificates.py       # Certificate management
│   ├── config_manager.py     # Configuration handling
│   ├── configurations.py     # Template configurations
│   ├── docker_manager.py     # Docker operations
│   ├── main.py               # Entry point
│   ├── wizard.py             # Main wizard interface
│   └── locales/              # Translation files
├── data/                     # User data directory
│   ├── configurations/       # Nginx configurations
│   ├── client_certs/         # Client certificates
│   └── server_certs/         # Server certificates
└── tests/                    # Test suite
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.