# Changelog

All notable changes to TeddyCloudStarter will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
- add password promt for private key generation for the client-certs at the moment its hardcoded "teddycloud"
- after entering domain, check if its a valid domain, check if public resolvable (Use DNS-Servers from Quad9), if not resolvable, hide let's encrypt option
After "? Would you like to start the Docker services now?" Open the Pre-Wizard no manage the configuration.
-after adding custom certificates check if they are nginx compatible. Should also check if .key is the correct .key for the certificate
## [0.3.2] - 2025-04-26
### Fixed
- .htpasswd creation
- client_certificates
## [0.3.1] - 2025-04-26
### Fixed
- Cross-platform imports
## [0.3.0] - 2025-04-26
### Added
- tonies.custom.json injection
### Fixed
- NGINX Configuration creation
- docker-compose.yml creation
- Docker Management
### Changed
- Backup/Restore
- Consolidate ProjectData
## [0.2.1] - 2025-04-22
### Changed global config 
- PyPi Workflow
## [0.2.1] - 2025-04-22
### Fixed
- PyPi Workflow
## [0.2.0] - 2025-04-22
### Added
- Initial alpha release after overhaul