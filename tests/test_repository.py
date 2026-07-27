from __future__ import annotations

import json
import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"


class RepositoryContractTests(unittest.TestCase):
    def test_complete_repository_files_exist(self) -> None:
        required = (
            "README.md",
            "LICENSE",
            "CONTRIBUTING.md",
            "SECURITY.md",
            "docs/USAGE.md",
            "docs/TROUBLESHOOTING.md",
            "examples/inputs/public-repository.json",
            "examples/api/run-scan.sh",
            "examples/api/run-scan.py",
            "examples/github-actions/iac-security-gate.yml",
            "examples/outputs/output.json",
            "examples/outputs/dataset-items.json",
            "scripts/check_links.py",
        )
        for relative_path in required:
            with self.subTest(path=relative_path):
                self.assertTrue((ROOT / relative_path).is_file())

    def test_readme_covers_the_todoist_acceptance_criteria(self) -> None:
        readme = README.read_text(encoding="utf-8")
        required_sections = (
            "## What this repository is for",
            "## Features",
            "## What you can test",
            "## Quick start",
            "## Visual walkthrough",
            "## Setup requirements",
            "## Repository structure",
            "## Run through the Apify API",
            "## Add an automated GitHub Actions gate",
            "## Configuration",
            "## Output contract",
            "## Use cases",
            "## FAQ and troubleshooting",
            "## Contributing",
            "## License",
            "## Run the Actor",
        )
        positions = [readme.index(section) for section in required_sections]
        self.assertEqual(positions, sorted(positions))

        required_phrases = (
            "deliberately insecure",
            "never deploy",
            "terraform",
            "kubernetes",
            "dockerfile",
            "cloudformation",
            "helm",
            "github actions",
            "apify_api_token",
            "pass",
            "fail",
            "unknown",
            "https://apify.com/kazkn/hosted-iac-policy-scan-api",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, readme.lower())

    def test_visual_walkthrough_uses_local_assets_and_links_to_live_proof(self) -> None:
        assets = (
            ROOT / "docs/assets/iac-scan-workflow.svg",
            ROOT / "docs/assets/apify-terraform-example.png",
            ROOT / "docs/assets/public-dataset-results.svg",
        )
        for asset in assets:
            with self.subTest(asset=asset.name):
                self.assertTrue(asset.is_file())
                self.assertGreater(asset.stat().st_size, 1_000)

        readme = README.read_text(encoding="utf-8")
        linked_images = [
            linked_image
            for linked_image in re.findall(
                r"\[!\[([^\]]+)\]\(([^)]+)\)\]\((https://[^)]+)\)",
                readme,
            )
            if linked_image[1].startswith("docs/assets/")
        ]
        self.assertEqual(
            linked_images,
            [
                (
                    "IaC scan workflow from source to Dataset and automation gate",
                    "docs/assets/iac-scan-workflow.svg",
                    "https://console.apify.com/actors/hrUBKuy93HIu7dBtp/input",
                ),
                (
                    "Public Terraform scan example on Apify",
                    "docs/assets/apify-terraform-example.png",
                    "https://apify.com/kazkn/hosted-iac-policy-scan-api/examples/"
                    "scan-terraform-security-misconfigurations",
                ),
                (
                    "Real normalized Terraform findings from the public Apify Dataset",
                    "docs/assets/public-dataset-results.svg",
                    "https://api.apify.com/v2/datasets/juCpMz5uiUXUi5Ggh/items"
                    "?clean=true&format=json",
                ),
            ],
        )

    def test_relative_markdown_links_resolve(self) -> None:
        markdown_files = tuple(ROOT.rglob("*.md"))
        link_pattern = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")

        for markdown_file in markdown_files:
            text = markdown_file.read_text(encoding="utf-8")
            for raw_target in link_pattern.findall(text):
                target = raw_target.split("#", 1)[0]
                if not target or target.startswith(("http://", "https://", "mailto:")):
                    continue
                resolved = (markdown_file.parent / target).resolve()
                with self.subTest(file=markdown_file, target=raw_target):
                    self.assertTrue(resolved.exists())

    def test_json_examples_are_valid_and_safe(self) -> None:
        input_example = json.loads(
            (ROOT / "examples/inputs/public-repository.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(input_example["sourceType"], "github")
        self.assertEqual(
            input_example["repositoryUrl"],
            "https://github.com/DataKazKN/iac-security-scan-examples",
        )
        self.assertRegex(input_example["repositoryRef"], r"^[0-9a-f]{40}$")
        self.assertEqual(input_example["subdirectory"], "fixtures/terraform")
        self.assertEqual(input_example["frameworks"], ["terraform"])
        self.assertEqual(input_example["policyProfile"], "security")
        self.assertGreaterEqual(input_example["maxFindings"], 1)
        self.assertLessEqual(input_example["maxFindings"], 500)
        self.assertNotIn("githubToken", input_example)

        output_example = json.loads(
            (ROOT / "examples/outputs/output.json").read_text(encoding="utf-8")
        )
        self.assertEqual(output_example["schemaVersion"], 2)
        self.assertIn(output_example["gateDecision"], {"PASS", "FAIL", "UNKNOWN"})
        self.assertNotIn("repositoryUrl", output_example)
        self.assertNotIn("githubToken", output_example)

        dataset_example = json.loads(
            (ROOT / "examples/outputs/dataset-items.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIsInstance(dataset_example, list)
        self.assertGreater(len(dataset_example), 0)
        self.assertTrue(all(item["result"] == "FAILED" for item in dataset_example))
        self.assertEqual(output_example["scanId"], dataset_example[0]["scanId"])

    def test_shell_example_has_valid_syntax_and_no_literal_token(self) -> None:
        script = ROOT / "examples/api/run-scan.sh"
        result = subprocess.run(
            ["bash", "-n", str(script)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        script_text = script.read_text(encoding="utf-8")
        self.assertIn("APIFY_API_TOKEN", script_text)
        self.assertNotRegex(script_text, r"apify_api_[A-Za-z0-9_-]+")

    def test_unsafe_workflow_stays_inert(self) -> None:
        unsafe_fixture = ROOT / "fixtures/.github/workflows/insecure.yml"
        self.assertTrue(unsafe_fixture.is_file())
        active_workflow = ROOT / ".github/workflows/validate.yml"
        if active_workflow.exists():
            active_text = active_workflow.read_text(encoding="utf-8")
            self.assertNotIn("pull_request_target", active_text)
            self.assertNotRegex(active_text, r"uses:\s+actions/[^@\s]+@v\d+")
            self.assertGreaterEqual(
                len(re.findall(r"uses:\s+actions/[^@\s]+@[0-9a-f]{40}", active_text)),
                2,
            )
        self.assertFalse((ROOT / ".github/workflows/insecure.yml").exists())

    def test_copy_ready_gate_scans_every_framework_covered_by_its_paths(self) -> None:
        workflow = (
            ROOT / "examples/github-actions/iac-security-gate.yml"
        ).read_text(encoding="utf-8")
        for framework in (
            "terraform",
            "cloudformation",
            "kubernetes",
            "helm",
            "dockerfile",
            "github_actions",
        ):
            with self.subTest(framework=framework):
                self.assertIn(f'"{framework}"', workflow)

    def test_original_fixture_paths_remain_stable(self) -> None:
        required_fixtures = (
            "fixtures/terraform/main.tf",
            "fixtures/kubernetes/deployment.yaml",
            "fixtures/dockerfile/Dockerfile",
            "fixtures/cloudformation/template.yaml",
            "fixtures/helm/Chart.yaml",
            "fixtures/helm/values.yaml",
            "fixtures/helm/templates/deployment.yaml",
            "fixtures/.github/workflows/insecure.yml",
        )
        for relative_path in required_fixtures:
            with self.subTest(path=relative_path):
                self.assertTrue((ROOT / relative_path).is_file())


if __name__ == "__main__":
    unittest.main()
