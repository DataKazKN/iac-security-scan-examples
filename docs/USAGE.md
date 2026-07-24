# Complete usage guide

This guide explains how to use the public fixtures and how to run the
[IaC Security Misconfiguration Scanner API](https://apify.com/kazkn/hosted-iac-policy-scan-api)
from Console, the API, or GitHub Actions.

> The files in `fixtures/` are deliberately insecure test data. Never deploy them.

## Choose a source

### Public GitHub repository

Use a full commit SHA for reproducibility:

```json
{
  "sourceType": "github",
  "repositoryUrl": "https://github.com/DataKazKN/iac-security-scan-examples",
  "repositoryRef": "ad600c04599f8a1d353639252ee12d2a5976a732",
  "subdirectory": "fixtures/terraform",
  "frameworks": ["terraform"],
  "policyProfile": "security",
  "checkIds": [],
  "maxFindings": 25
}
```

The Actor downloads a GitHub archive. It does not clone the repository, execute
hooks, follow submodules, or modify the source.

### Private GitHub repository

Add `githubToken` as a secret Actor input. Use a fine-grained GitHub token with
read-only **Contents** access to only the repository being scanned:

```json
{
  "sourceType": "github",
  "repositoryUrl": "https://github.com/your-organization/private-infrastructure",
  "repositoryRef": "your-full-40-character-commit-sha",
  "subdirectory": "infra",
  "githubToken": "use-the-secret-input",
  "frameworks": ["terraform"],
  "policyProfile": "security",
  "checkIds": [],
  "maxFindings": 500
}
```

Never place the token in the repository URL, ref, task name, webhook, ZIP, or log.

### ZIP upload

In Apify Console, choose **Uploaded ZIP** and select a ZIP up to 20 MiB. Console
stores it in an authenticated Key-Value Store record. API clients must upload the
file to Apify storage first and pass that record URL as `archiveFile`.

The ready-to-upload [`iac-public-s3-smoke.zip`](../fixtures/upload/iac-public-s3-smoke.zip)
contains one deliberately public S3 bucket and no secrets.

## Inputs

| Input | Type | Rules |
|---|---|---|
| `sourceType` | string | Exactly `github` or `zip_upload` |
| `repositoryUrl` | string | Exact GitHub HTTPS repository URL; GitHub source only |
| `repositoryRef` | string | Optional branch/tag; full 40-character SHA recommended |
| `subdirectory` | string | Optional relative POSIX path |
| `archiveFile` | string | Authenticated Apify KVS record URL; ZIP source only |
| `githubToken` | secret string | Optional private-repository token |
| `frameworks` | string array | One or more supported framework slugs |
| `policyProfile` | string | `security` excludes convention checks; `all_iac` includes them |
| `checkIds` | string array | Up to 100 unique Checkov IDs |
| `maxFindings` | integer | 1–500 retained Dataset rows |

Supported frameworks:

`ansible`, `argo_workflows`, `arm`, `azure_pipelines`, `bicep`,
`bitbucket_pipelines`, `cdk`, `circleci_pipelines`, `cloudformation`, `dockerfile`,
`github_actions`, `gitlab_ci`, `helm`, `kubernetes`, `kustomize`, `openapi`,
`serverless`, `terraform`, `terraform_json`, and `terraform_plan`.

The Actor supports static IaC policies only. It excludes secrets scanning,
dependency scanning, image scanning, live-cloud checks, custom Python checks,
external checks, and remote Terraform-module downloads.

## Run with the API examples

Set your token locally:

```bash
export APIFY_API_TOKEN="your_token"
```

Run the shell client:

```bash
./examples/api/run-scan.sh
./examples/api/run-scan.sh --enforce
```

Or the dependency-free Python client:

```bash
python3 examples/api/run-scan.py
python3 examples/api/run-scan.py --enforce
```

Both examples:

1. start `kazkn~hosted-iac-policy-scan-api`;
2. bound the total charge at `$0.51`;
3. wait up to 120 seconds for the API request;
4. require the Actor run to succeed technically;
5. fetch the `OUTPUT` KVS record and Dataset items;
6. optionally enforce `gateDecision = PASS`.

See Apify’s official
[Run Actor API reference](https://docs.apify.com/api/v2/act-runs-post) for endpoint
parameters.

## Output semantics

### Dataset

The default Dataset contains failed policies only, up to `maxFindings`. Each row
includes:

- `framework`, `checkId`, and `checkName`;
- affected `resource`, `filePath`, and optional line range;
- native Checkov categories and deterministic primary category;
- `severity = UNRATED`;
- stable finding fingerprint and pinned policy reference;
- `result = FAILED` and the pinned scanner version.

Review [`examples/outputs/dataset-items.json`](../examples/outputs/dataset-items.json).

### OUTPUT

The `OUTPUT` record is the automation summary. It includes:

- technical `status`;
- `gateDecision`;
- scanner and framework metadata;
- passed, failed, skipped, retained, and total-finding counts;
- source-size statistics;
- category totals;
- truncation reasons, warnings, and a safe error object when applicable.

Review [`examples/outputs/output.json`](../examples/outputs/output.json).

### Status versus gate decision

`COMPLETED_WITH_FINDINGS` means the scanner completed successfully and found policy
failures. It normally pairs with `gateDecision = FAIL`.

- `PASS`: completed with zero selected policy failures.
- `FAIL`: completed with one or more selected policy failures.
- `UNKNOWN`: no trustworthy policy decision because of a technical failure.

In an enforcement workflow, only `PASS` should continue.

## Pricing and hard limits

The completed-scan event costs `$0.25–$0.50` according to the customer’s Apify
subscription tier, plus the configured Actor-start platform event. The examples use
`maxTotalChargeUsd=0.51` to bound a single run.

Current documented bounds:

- ZIP: 20 MiB compressed;
- up to 500 files and 100 MiB uncompressed;
- 50 MiB per file and 100:1 expansion ratio;
- Checkov subprocess timeout: 60 seconds;
- up to 100 Check IDs;
- 1–500 retained Dataset findings.

Use the Actor’s
[Store documentation](https://apify.com/kazkn/hosted-iac-policy-scan-api) as the
current source for pricing, security boundaries, and runtime limits.

## Test this repository

```bash
python3 -m unittest discover -s tests -v
python3 scripts/check_links.py --local-only
python3 scripts/check_links.py --http
```

The last command performs network requests to every unique public Markdown URL and
fails if any target does not return an HTTP success response.
