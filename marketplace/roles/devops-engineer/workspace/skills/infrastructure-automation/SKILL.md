---
name: infrastructure-automation
description: "Infrastructure as Code and automation practices. Use when provisioning, managing, or troubleshooting infrastructure."
metadata: {"clawbot":{"emoji":"🏗️"}}
---

# Infrastructure Automation

## IaC Principles

1. **Version control** — All infra in git
2. **Idempotency** — Apply repeatedly, same result
3. **Immutability** — Replace, don't modify
4. **Modularity** — Reusable components
5. **Self-documenting** — Code is the documentation

## Terraform Best Practices

### Project Structure

```
infrastructure/
├── modules/
│   ├── vpc/
│   ├── eks/
│   └── rds/
├── environments/
│   ├── dev/
│   ├── staging/
│   └── prod/
├── backend.tf
└── versions.tf
```

### State Management

```hcl
terraform {
  backend "s3" {
    bucket         = "company-terraform-state"
    key            = "env/terraform.tfstate"
    region         = "us-west-2"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}
```

### Resource Naming

```hcl
locals {
  name_prefix = "${var.project}-${var.environment}"
}

resource "aws_instance" "web" {
  tags = {
    Name        = "${local.name_prefix}-web"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}
```

## Docker Best Practices

### Dockerfile Optimization

```dockerfile
# Multi-stage build
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production image
FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
USER node
EXPOSE 3000
CMD ["node", "dist/main.js"]
```

### Image Security

- Use official base images
- Pin versions (not `latest`)
- Scan for vulnerabilities
- Run as non-root user
- Minimize image size

## Kubernetes Essentials

### Deployment Template

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: app
  template:
    metadata:
      labels:
        app: app
    spec:
      containers:
        - name: app
          image: app:v1.0.0
          ports:
            - containerPort: 8080
          resources:
            requests:
              memory: "128Mi"
              cpu: "100m"
            limits:
              memory: "256Mi"
              cpu: "200m"
          readinessProbe:
            httpGet:
              path: /health
              port: 8080
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
```

## Automation Checklist

- [ ] Infrastructure in version control
- [ ] CI/CD for infrastructure changes
- [ ] State stored remotely with locking
- [ ] Secrets managed securely
- [ ] Environments are isolated
- [ ] Drift detection enabled
- [ ] Rollback procedures documented
