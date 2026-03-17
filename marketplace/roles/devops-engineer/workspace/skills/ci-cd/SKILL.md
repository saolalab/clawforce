---
name: ci-cd
description: "CI/CD pipeline design and management. Use when building, troubleshooting, or optimizing build and deployment pipelines."
metadata: {"clawbot":{"emoji":"🔄"}}
---

# CI/CD Pipelines

## Pipeline Architecture

```
Commit → Build → Test → Security Scan → Deploy → Verify → Monitor
```

## Pipeline Best Practices

### Build Stage
- **Reproducible builds** — Same input = same output
- **Caching** — Cache dependencies, build artifacts
- **Parallel execution** — Run independent jobs concurrently
- **Artifact versioning** — Tag artifacts with commit SHA

### Test Stage
- **Fast feedback** — Unit tests first, integration later
- **Parallelization** — Split test suites across workers
- **Flaky test management** — Quarantine, don't ignore
- **Coverage gates** — Block PRs below threshold

### Security Stage
- **SAST** — Static analysis on every commit
- **Dependency scanning** — Check for known CVEs
- **Secret scanning** — Prevent credential leaks
- **Container scanning** — Scan images before deploy

### Deploy Stage
- **Environment promotion** — Dev → Staging → Prod
- **Deployment gates** — Approval for production
- **Rollback capability** — One-click rollback
- **Blue-green/Canary** — Safe production deployments

## GitHub Actions Example

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run build
      - uses: actions/upload-artifact@v4
        with:
          name: build
          path: dist/

  test:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm test -- --coverage

  deploy:
    needs: [build, test]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4
      - run: ./deploy.sh
```

## Metrics to Track

| Metric | Target | Description |
|--------|--------|-------------|
| Build time | < 10 min | Time from commit to artifacts ready |
| Test time | < 15 min | Time for full test suite |
| Deploy time | < 5 min | Time to deploy to production |
| Pipeline success rate | > 95% | % of pipelines completing successfully |
| Deployment frequency | Daily+ | How often we deploy to production |
| Lead time | < 1 day | Commit to production |

## Troubleshooting

### Common Issues

1. **Flaky tests** — Add retries, improve isolation
2. **Slow builds** — Profile, cache, parallelize
3. **OOM errors** — Increase resources or optimize
4. **Timeouts** — Check network, increase limits
5. **Permission errors** — Verify service account access
