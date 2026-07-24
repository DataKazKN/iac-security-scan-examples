#!/usr/bin/env bash
set -euo pipefail

: "${APIFY_API_TOKEN:?Set APIFY_API_TOKEN in the environment}"

actor_id="${APIFY_ACTOR_ID:-kazkn~hosted-iac-policy-scan-api}"
api_base="https://api.apify.com/v2"
max_charge_usd="${APIFY_MAX_CHARGE_USD:-0.51}"
enforce_gate=false

if [[ "${1:-}" == "--enforce" ]]; then
  enforce_gate=true
elif [[ -n "${1:-}" ]]; then
  echo "Usage: $0 [--enforce]" >&2
  exit 64
fi

for command_name in curl jq; do
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    echo "Required command not found: ${command_name}" >&2
    exit 127
  fi
done

input_json=$(jq -cn '{
  sourceType: "github",
  repositoryUrl: "https://github.com/DataKazKN/iac-security-scan-examples",
  repositoryRef: "ad600c04599f8a1d353639252ee12d2a5976a732",
  subdirectory: "fixtures/terraform",
  frameworks: ["terraform"],
  policyProfile: "security",
  checkIds: [],
  maxFindings: 25
}')

run_json=$(curl --fail-with-body --silent --show-error \
  --request POST \
  "${api_base}/acts/${actor_id}/runs?waitForFinish=120&maxTotalChargeUsd=${max_charge_usd}" \
  --header "Authorization: Bearer ${APIFY_API_TOKEN}" \
  --header "Content-Type: application/json" \
  --data "${input_json}")

run_status=$(jq -er '.data.status' <<<"${run_json}")
if [[ "${run_status}" != "SUCCEEDED" ]]; then
  echo "Actor run did not succeed: ${run_status}" >&2
  exit 1
fi

store_id=$(jq -er '.data.defaultKeyValueStoreId' <<<"${run_json}")
dataset_id=$(jq -er '.data.defaultDatasetId' <<<"${run_json}")

output_json=$(curl --fail-with-body --silent --show-error \
  "${api_base}/key-value-stores/${store_id}/records/OUTPUT" \
  --header "Authorization: Bearer ${APIFY_API_TOKEN}")

dataset_json=$(curl --fail-with-body --silent --show-error \
  "${api_base}/datasets/${dataset_id}/items?clean=true&limit=10" \
  --header "Authorization: Bearer ${APIFY_API_TOKEN}")

echo "OUTPUT"
jq . <<<"${output_json}"
echo "DATASET (first 10 rows)"
jq . <<<"${dataset_json}"

gate_decision=$(jq -er '.gateDecision' <<<"${output_json}")
echo "Gate decision: ${gate_decision}"

if [[ "${enforce_gate}" == true && "${gate_decision}" != "PASS" ]]; then
  echo "IaC security gate blocked: ${gate_decision}" >&2
  exit 2
fi
