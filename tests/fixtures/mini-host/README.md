# Mini Host

[![CI](https://img.shields.io/badge/ci-passing-brightgreen.svg)](https://example.com/ci)

Mini Host is a small command line tool that prints a greeting. It is a test fixture for cc-guide's embedded mode.

## Install

Install the tool with `uv tool install mini-host`. The [install notes](docs/install.md) cover the details.

## Usage

Run `mini-host greet` to print a greeting. The greeting text comes from `config/defaults.yaml`. See [USAGE.md](USAGE.md) for all commands.

## Building from source

Clone the repository and run `make build`. Read the [install notes](docs/install.md) and [CONTRIBUTING.md](CONTRIBUTING.md) first.

### Requirements

Python 3.11 or later and uv.

## Running tests

Run `make test`. The test runner reads `pyproject.toml`.
