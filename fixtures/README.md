# Public IaC task fixtures

Deliberately insecure examples — never deploy

These files exist only to produce deterministic scanner findings for public task
examples. Every resource name is a non-secret placeholder, and no file contains a
credential, account identifier, private URL, real endpoint, or deployment command.

The Dockerfile demonstrates only Dockerfile and IaC policy misconfigurations. This
fixture does not scan container images or their installed packages.

## Safe public mirroring

When mirroring this pack publicly, keep the entire pack under the non-root `fixtures/`
prefix so `fixtures/.github/workflows/insecure.yml` remains inert. Never copy this
workflow to the repository root, where GitHub Actions could execute it.
