# Contributing

Contributions should make these examples easier to reproduce without making the
repository dangerous to use.

## Fixture rules

Every new fixture must:

1. live below `fixtures/`;
2. be deliberately insecure for one or more documented policy checks;
3. use only fake names and public placeholder values;
4. contain no credential, token, private URL, real account ID, or deploy command;
5. remain deterministic when scanned from a pinned commit;
6. document its intended finding in the root `README.md`;
7. preserve existing fixture paths used by public Apify examples.

An unsafe GitHub Actions sample must stay below `fixtures/.github/workflows/`. Never
place `pull_request_target`, write permissions, or an intentionally vulnerable
workflow in the repository’s active `.github/workflows/` directory.

## API and CI examples

- Read tokens from `APIFY_API_TOKEN`; never hardcode them.
- Pin public example sources to a full 40-character Git commit SHA.
- Treat `PASS` as continue, and both `FAIL` and `UNKNOWN` as block when enforcement
  is enabled.
- Keep the maximum charge explicit and bounded.
- Do not log private-repository tokens or include them in URLs.

## Validate a change

The test suite uses only Python’s standard library:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/check_links.py --local-only
python3 scripts/check_links.py --http
```

The HTTP check requires network access. It validates every public URL referenced by
the repository’s Markdown files.

## Pull-request checklist

- [ ] Existing public fixture paths are unchanged.
- [ ] No real infrastructure should be deployed from the change.
- [ ] No credential or private identifier is present.
- [ ] The expected finding is documented.
- [ ] JSON and shell examples pass the contract tests.
- [ ] Relative links resolve and public links return HTTP success.

By contributing, you agree that your contribution is licensed under the repository’s
[MIT License](LICENSE).
