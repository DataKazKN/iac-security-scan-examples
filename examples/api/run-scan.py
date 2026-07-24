#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_BASE = "https://api.apify.com/v2"
DEFAULT_ACTOR_ID = "kazkn~hosted-iac-policy-scan-api"
INPUT = {
    "sourceType": "github",
    "repositoryUrl": "https://github.com/DataKazKN/iac-security-scan-examples",
    "repositoryRef": "ad600c04599f8a1d353639252ee12d2a5976a732",
    "subdirectory": "fixtures/terraform",
    "frameworks": ["terraform"],
    "policyProfile": "security",
    "checkIds": [],
    "maxFindings": 25,
}


def request_json(
    url: str,
    token: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> Any:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "iac-security-scan-examples/1.0",
        },
    )
    with urlopen(request, timeout=150) as response:
        return json.load(response)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the public IaC scan example.")
    parser.add_argument(
        "--enforce",
        action="store_true",
        help="Return exit code 2 unless gateDecision is PASS.",
    )
    args = parser.parse_args()

    token = os.environ.get("APIFY_API_TOKEN")
    if not token:
        print("Set APIFY_API_TOKEN in the environment.", file=sys.stderr)
        return 64

    actor_id = os.environ.get("APIFY_ACTOR_ID", DEFAULT_ACTOR_ID)
    max_charge = os.environ.get("APIFY_MAX_CHARGE_USD", "0.51")
    query = urlencode(
        {"waitForFinish": "120", "maxTotalChargeUsd": max_charge}
    )

    try:
        run = request_json(
            f"{API_BASE}/acts/{actor_id}/runs?{query}",
            token,
            method="POST",
            payload=INPUT,
        )["data"]
        if run["status"] != "SUCCEEDED":
            print(f"Actor run did not succeed: {run['status']}", file=sys.stderr)
            return 1

        output = request_json(
            f"{API_BASE}/key-value-stores/{run['defaultKeyValueStoreId']}/records/OUTPUT",
            token,
        )
        dataset = request_json(
            f"{API_BASE}/datasets/{run['defaultDatasetId']}/items?clean=true&limit=10",
            token,
        )
    except (HTTPError, URLError, KeyError, json.JSONDecodeError) as error:
        print(f"API request failed: {error}", file=sys.stderr)
        return 1

    print("OUTPUT")
    print(json.dumps(output, indent=2))
    print("DATASET (first 10 rows)")
    print(json.dumps(dataset, indent=2))

    gate_decision = output.get("gateDecision", "UNKNOWN")
    print(f"Gate decision: {gate_decision}")
    if args.enforce and gate_decision != "PASS":
        print(f"IaC security gate blocked: {gate_decision}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
