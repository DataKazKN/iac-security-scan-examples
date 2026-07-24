# Security policy

## Expected insecure content

Misconfigurations inside `fixtures/` are intentional and are not vulnerabilities in
this repository. They exist to make scanners return deterministic findings.

## Report a real repository security issue

Please report any of the following privately:

- an accidentally committed credential or private identifier;
- an unsafe workflow placed in the active `.github/workflows/` directory;
- a script that leaks `APIFY_API_TOKEN` or another secret;
- a path or instruction that could unexpectedly deploy a fixture.

Use GitHub’s private vulnerability-reporting flow from this repository’s
**Security** tab when it is available. Do not paste credentials into a public issue,
pull request, discussion, log, or screenshot.

For issues in the hosted Actor rather than this examples repository, use the support
channel on the
[IaC Security Misconfiguration Scanner API page](https://apify.com/kazkn/hosted-iac-policy-scan-api).

## Supported version

Only the current `main` branch is maintained. Historical commits remain available
for reproducible public examples but do not receive documentation or security
updates.
