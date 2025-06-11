# Documentation Maintenance Guide

## Overview

This guide establishes the requirements and procedures for maintaining up-to-date documentation in the Swisper Core project. All contributors must follow these guidelines to ensure documentation accuracy and completeness.

## Pre-PR Documentation Requirements

Before creating any Pull Request, the following documentation checks must be completed:

### 1. Architecture Documentation Review

**Required Actions:**
- Review and update architecture diagrams in `docs/architecture/overview.md` if system components have changed
- Verify that the PlantUML diagrams accurately reflect current module structure and dependencies
- Update component interaction flows if new services or pipelines have been added
- Ensure the `swisper_core` shared module relationships are correctly represented

**Key Files to Check:**
- `docs/architecture/overview.md` - Main architecture diagrams and component descriptions
- `docs/intent_extraction_architecture.md` - Intent classification system architecture
- `docs/architecture/tools-and-contracts.md` - FSM and pipeline integration
- `docs/architecture/session-management.md` - Session persistence and context management
- `docs/architecture/memory-management.md` - Multi-tier memory architecture

### 2. API Documentation Updates

**Required Actions:**
- Update API documentation in `docs/api/` if new endpoints, methods, or interfaces have been added
- Verify all code examples use correct import statements and reflect current implementation
- Update parameter descriptions and return value documentation
- Ensure all new public methods and classes are documented

**Key Files to Check:**
- `docs/api/API_DOCUMENTATION.md` - Core APIs for pipelines, FSM, and session management
- `docs/api/MEMORY_MANAGER_API.md` - Memory management service API reference

### 3. Configuration and Setup Documentation

**Required Actions:**
- Update configuration guides if new environment variables, dependencies, or setup steps are required
- Verify installation and setup instructions are current
- Update deployment documentation if infrastructure changes have been made

**Key Files to Check:**
- `docs/configuration/REDIS_CONFIGURATION.md` - Redis setup and optimization
- `docs/deployment/` - Production and local setup guides
- Main `README.md` - Installation and quick start instructions

### 4. Technical Guides and References

**Required Actions:**
- Update technical guides if implementation details have changed
- Verify code examples and usage patterns are current
- Update troubleshooting sections with new known issues or solutions

**Key Files to Check:**
- `docs/guides/T5_USAGE_GUIDE.md` - Local T5 model integration
- `docs/guides/T5_API_REFERENCE.md` - T5 model API documentation
- `docs/testing/` - Testing strategy and scenarios

## Documentation Review Checklist

Before submitting a PR, complete this checklist:

### Architecture Changes
- [ ] Reviewed `docs/architecture/overview.md` for accuracy
- [ ] Updated PlantUML diagrams if component structure changed
- [ ] Verified `swisper_core` module relationships are correct
- [ ] Updated component interaction flows if needed
- [ ] Checked intent extraction architecture documentation

### Code Changes
- [ ] Updated API documentation for new/modified endpoints
- [ ] Verified all code examples use correct imports
- [ ] Updated parameter and return value documentation
- [ ] Added documentation for new public methods/classes

### Configuration Changes
- [ ] Updated configuration documentation
- [ ] Verified setup and installation instructions
- [ ] Updated deployment guides if needed
- [ ] Checked environment variable documentation

### Testing and Validation
- [ ] Ran `poetry run pylint` to verify no broken imports in documentation examples
- [ ] Tested all documentation links work correctly
- [ ] Verified code examples execute without errors
- [ ] Checked that architecture diagrams render correctly

## Documentation Standards

### Code Examples
- All code examples must use current import paths (especially `swisper_core` imports)
- Examples should be executable and tested
- Include error handling where appropriate
- Use realistic parameter values

### Architecture Diagrams
- Use PlantUML format for consistency
- Include all major components and their relationships
- Show data flow and control flow clearly
- Update diagrams when component structure changes

### Cross-References
- Link related documentation sections
- Maintain consistent terminology across documents
- Update internal links when files are moved or renamed

## Enforcement

### PR Review Process
- Documentation updates are mandatory for PRs that modify system architecture
- Reviewers must verify documentation accuracy before approving PRs
- CI checks should validate documentation links and code examples

### Automated Checks
- Link validation in CI pipeline
- Code example syntax checking
- Import statement verification
- Architecture diagram rendering tests

## Maintenance Schedule

### Regular Reviews
- Monthly architecture documentation review
- Quarterly comprehensive documentation audit
- Update documentation index when new files are added

### Triggered Updates
- After major feature additions
- When new components or services are added
- After significant refactoring
- When external dependencies change

## Contact and Support

For questions about documentation requirements or assistance with updates:
- Review existing documentation in `docs/README.md`
- Check architecture documentation in `docs/architecture/`
- Refer to API documentation in `docs/api/`

## Compliance Notes

This documentation maintenance process supports:
- **Swiss Data Sovereignty**: Ensures local processing capabilities are properly documented
- **System Reliability**: Maintains accurate system understanding for all contributors
- **Development Efficiency**: Reduces onboarding time and development confusion
- **Audit Requirements**: Provides clear documentation trail for compliance purposes
