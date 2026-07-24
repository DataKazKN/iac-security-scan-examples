# Troubleshooting

## The quick start returns `FAIL`

That is the expected result. The public Terraform fixture deliberately grants public
read access to an S3 bucket. The scan should complete technically with
`COMPLETED_WITH_FINDINGS`, while the policy gate returns `FAIL`.

## The gate returns `UNKNOWN`

`UNKNOWN` is not a clean scan. It means the Actor could not produce a trustworthy
policy decision.

1. Open the KVS `OUTPUT` record.
2. Read `error.code`, `error.message`, and `error.hint`.
3. Correct the input, access, archive, scanner, persistence, or billing issue.
4. Run a new scan and require a new explicit `PASS`.

Never convert `UNKNOWN` into `PASS`.

## The Actor run is not `SUCCEEDED`

Inspect the run log and `OUTPUT`. A policy failure does not make the Actor run fail;
it produces `SUCCEEDED` with `COMPLETED_WITH_FINDINGS`. A failed Actor run indicates
a technical or billing problem.

## GitHub returns `404`

- Confirm `repositoryUrl` is exactly `https://github.com/{owner}/{repository}`.
- Confirm the full commit SHA belongs to that repository.
- Remove query strings, fragments, `/tree/...`, and embedded credentials.
- For a private repository, supply a fine-grained token with read-only Contents
  access to only that repository.

GitHub may intentionally return `404` when a private repository is not visible to
the supplied token.

## A subdirectory is rejected

Use a relative POSIX path such as `infra/terraform`. Do not use an absolute path,
backslashes, `..`, a URL, or a path outside the extracted repository.

## The ZIP is rejected

The Actor accepts stored or deflated, unencrypted ZIP entries. It rejects oversized
archives, traversal paths, absolute paths, symlinks, devices, collisions, nested
archives, unsupported compression, and expansion-ratio violations.

Use the Console file picker or an authenticated Apify Key-Value Store record. Local
paths and arbitrary public URLs are not valid `archiveFile` inputs.

## GitHub Actions cannot see `APIFY_API_TOKEN`

Create the secret in the repository or organization that runs the workflow. Forked
pull requests do not receive repository secrets by default.

Do not solve this by logging the token, placing it in YAML, using
`pull_request_target` with untrusted checkout, or granting write permissions.

## The maximum charge is rejected

The examples use `$0.51`, which covers the documented Free-tier completed-scan price
and Actor-start event at the current configuration. If Apify pricing changes, review
the current
[Actor pricing](https://apify.com/kazkn/hosted-iac-policy-scan-api) before changing
the cap.

## Findings are truncated

`maxFindings` limits Dataset rows, not the complete failure count. Read
`totalFindingCount`, `findingCount`, `truncated`, and `truncationReasons` in
`OUTPUT`. Raise `maxFindings` up to 500 if the additional rows are necessary.

## A finding has `severity = UNRATED`

`UNRATED` does not mean low risk. The Actor intentionally does not invent
exploitability or severity data. Review the check, affected resource, source lines,
native categories, and pinned policy reference.

## Helm or Kustomize behaves differently

Pin the source commit, keep the Actor’s current framework slug, and compare the
result with the Actor Store documentation. The hosted build pins its scanner and
image tools, but upstream template behavior can still evolve between Actor builds.

## A documentation link is broken

From the repository root:

```bash
python3 scripts/check_links.py --local-only
python3 scripts/check_links.py --http
```

The first command checks repository-relative paths. The second also requires every
public Markdown URL to return HTTP success.
