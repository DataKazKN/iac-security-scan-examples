# IaC security scan examples

Deliberately insecure examples — never deploy.

This repository contains small, deterministic fixtures for testing static IaC
misconfiguration scanners across Terraform, Kubernetes YAML, Dockerfile,
AWS CloudFormation, Helm, and GitHub Actions syntax.

All samples live under `fixtures/`. The intentionally unsafe workflow therefore
remains at `fixtures/.github/workflows/insecure.yml` and cannot run as a repository
workflow. GitHub Actions is also disabled for this repository as defense in depth.

The files contain no credentials, real cloud account identifiers, private URLs, or
deployment commands. They exist only to produce stable scanner findings.
