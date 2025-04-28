# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

### [Unreleased]

### ToDo
- double check dockerfile

### Work In Progress

### Bugs/Hotfix

### Updated
04/27/2025
- moved constant to config

04/12/2025
- downgraded `python` image to `v3.10.12-slim`
- reduced `benchmark_time` to `150` (2.5 minutes)
- reduced `max_temp` to `65c`
- reduced `max_vr_temp` to `75c`
- increased `max_power` to `45w`
- increased `min_allowed_voltage` to `1150mV`
- increased `min_allowed_frequency` to `525MHz`
- increased `frequency` default value to `525MHz`
- removed whitespace
- moved configuration to `constants.py`
- always download the latest `requests`
- updated project structure
- updated Dockerfile

### Added
04/28/2025
- implemented unit test with coverage for services' class

04/26/2025
- implemented results_service and system_service
- added pylint configuration

04/12/2025
- Added `CHANGELOG.md`
- implemented some improvements
- added pylint
- implemented benchmark service
- implemented `Makefile` for `build` and `run` commands
