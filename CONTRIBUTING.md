# Contributing to Clawforce

Thank you for your interest in contributing!

## Development Setup

```bash
# Clone the repository
git clone https://github.com/saolalab/clawforce.git
cd clawforce

# Install dependencies
make install

# Create admin user
make setup

# Run development servers
make backend   # Terminal 1
make frontend  # Terminal 2
```

## Running Tests

```bash
make test
```

## Code Style

We use `ruff` for linting and formatting:

```bash
make lint       # Check for issues
make lint-fix   # Auto-fix lint issues
make format     # Auto-format code
```

## Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests: `make test`
5. Run linter: `make lint`
6. Commit with a descriptive message
7. Push and open a PR

## Releasing (Maintainers)

Releases are automated via GitHub Actions. **Version is not stored in the repo** — it comes from git tags (or the workflow input in CI). Member packages use `hatch-vcs` to derive version from git; locally you get `0.0.0.dev0` when there is no tag.

To create a new release you only need to provide the version in the workflow (or push a tag).

**Option A — Version input only (recommended):**

1. In GitHub: **Actions → Release → Run workflow**. Enter the version (e.g. `0.1.2`) in the **version** input and run.
2. The workflow runs from the current commit, uses that version for builds and the GitHub release, and creates tag `vX.Y.Z`. No file edits.

**Option B — Manual tag:**

1. Create and push the tag: `git tag vX.Y.Z && git push origin vX.Y.Z`.
2. The push of the tag triggers the Release workflow (version is taken from the tag).

In both options, the Release workflow runs tests, builds and pushes the Docker image, publishes the bridge npm package (if applicable), and creates the GitHub release.

### Version Numbering

We follow [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### PyPI Publishing

Python packages (`clawlib`, `clawbot`, `clawforce`) are built as part of CI (`ci.yml`) and uploaded as artifacts, but are not automatically published to PyPI in the current release workflow. To publish to PyPI, use [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC, no API tokens needed). If you add a PyPI publish step to `release.yml`, configure a trusted publisher in PyPI for each package:
- Repository: `saolalab/clawforce`
- Workflow: `release.yml`
- Environment: `release`

## Project Structure

```
├── clawlib/         # Shared library (published first)
├── clawbot/         # Agent framework (depends on clawlib)
├── clawforce/       # Admin control plane (depends on both)
├── clawforce-ui/    # Admin dashboard (React)
├── bridges/         # Node.js bridges (whatsapp, zalo)
└── tests/           # Test suite
```

## Questions?

Open an issue on GitHub!
