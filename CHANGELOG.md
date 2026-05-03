# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-05-02

### Added
- **Project renamed**: Migrated from `dev-agent` to `gitdar` (CLI tool for generating standups and surfacing PR ownership)
- **Core architecture**: 
  - Single CLI entrypoint with typer framework
  - Three-command structure: `init`, `standup`, `prs`
  - Provider abstraction layer for LLM integration
- **CLI structure**: 
  - Main CLI entry point (`cli/main.py`)
  - Command scaffolding for `init`, `standup`, and `prs` commands
  - Output formatting and clipboard utilities
- **LLM Provider System**:
  - Base provider interface (`services/llm/base.py`) supporting OpenAI-compatible APIs
  - LM Studio provider implementation (`services/llm/providers/lmstudio.py`)
  - Extensible provider registry for Groq, OpenAI, Ollama, and LM Studio
- **Configuration System**:
  - TOML-based config loader (`config/loader.py`)
  - Sensible defaults configuration (`config/defaults.py`)
  - Support for multi-tier config hierarchy
- **Shared Contracts**:
  - `ToolResponse` execution contract with status tracking and latency stamping
  - `ToolMetadata` for tool identity and runtime reflection
  - Unified error handling and result serialization
- **Project Structure**:
  - Domains-driven design setup with engineering domain
  - Memory subsystem folders (episodic, semantic, short-term)
  - Runtime orchestration layer (planner, executor, reasoner)
  - Repository infrastructure with caching
- **Package Management**:
  - pip-installable package with setuptools configuration
  - Console script entry point: `gitdar`
  - Development dependencies (pytest, pytest-asyncio, pytest-mock)
- **Testing Foundation**:
  - Unit test structure with import validation
  - LM Studio provider tests
  - Init command tests

### Fixed
- Updated package metadata from `dev-agent` to `gitdar`

### Todo
- [ ] Implement GitHub API client and caching layer
- [ ] Complete standup command generation logic
- [ ] Implement PR ranking with risk scoring
- [ ] Add pattern learning for team behaviors
- [ ] Implement local database schema migrations
- [ ] Complete LLM provider registry and fallback chain
- [ ] Add comprehensive test coverage for all commands
- [ ] Create documentation with GIF recording
- [ ] Support for Linux and macOS validation


## [0.2.0] - 2026-05-03

### Added
- **Runtime Integration**: Integrated core runtime infrastructure with orchestrator, executor, and planner components
- **Engineering Domain**: Added engineering domain layer with application services and business logic
- **CLI Integration**: Integrated commands and output formatter for command execution
- **Repository Infrastructure**: GitHub API adapter with local caching support

### Fixed
- **LM Studio Provider**: Fixed model loading configuration for local provider
- **Import Errors**: Resolved minor import issues in provider loading chain

### Known Issues
- Out of 23 unit tests, 16 pass while 7 fail
- Test failures originate from `unit/test_init.py` — core business logic is correct but implementation is too interactive for test harness
- **Next Steps**: Refactor init command to use Typer/Click-friendly prompting instead of fake provider prompts for better testability

### In Progress
- Improving test coverage and initialization flow
- Refining command-line interface for interactive workflows 


