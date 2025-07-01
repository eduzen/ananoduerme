# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a minimal Python project called "ananoduerme" with a simple structure. The project uses Python 3.13+ and is managed with a pyproject.toml configuration.

## Development Commands

### Running the Application
```bash
python main.py
```

### Python Environment
- Python version: 3.13+ (specified in .python-version)
- No external dependencies currently defined
- Uses pyproject.toml for project configuration

## Project Structure

- `main.py` - Entry point with a simple main() function that prints a greeting
- `pyproject.toml` - Project configuration and metadata
- `.python-version` - Specifies Python 3.13 for version management tools
- `.gitignore` - Standard Python gitignore covering common build artifacts and virtual environments

## Architecture Notes

This is a minimal Python project in its initial state. The main.py file contains only a basic greeting function. The project structure suggests it's set up for future development with proper Python packaging conventions via pyproject.toml.

## Dependency Management
- Remember that this beginning of the file is for uv, it's the new standard for running scripts with dependencies defined.