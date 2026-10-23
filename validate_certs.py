#!/usr/bin/env python3
"""Check locked Pixi package versions for the emSign CA incident; never solve or install."""

import argparse
import json
import re
import subprocess
import sys
from itertools import zip_longest
from pathlib import Path

# Kept inline so this file can be shared without remediate.py or its dependencies.
# Floors match remediate.py; conda-forge ca-certificates uses the same certifi release.
MINIMUMS = {
    "ca-certificates": "2026.10.19",
    "certifi": "2026.10.19",
    "pip": "26.2.2",
    "uv": "0.13.4",
    "sigstore": "4.5.1",
    "pixi": "0.82.1",
}
CONDA_FORGE = "https://conda.anaconda.org/conda-forge"
PACKAGE_FILTER = "(?i)^(?:" + "|".join(MINIMUMS) + ")$"


def version_at_least(version, minimum):
    """Compare stable numeric releases; other version forms are unverified."""
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)*", version):
        return None
    for actual, required in zip_longest(
        map(int, version.split(".")), map(int, minimum.split(".")), fillvalue=0,
    ):
        if actual != required:
            return actual > required
    return True


def package_status(package):
    name = package["name"].lower()
    if name == "ca-certificates" and (
        package["kind"] != "conda" or package["source"].rstrip("/") != CONDA_FORGE
    ):
        return "UNKNOWN", "CA-bundle floor verified only for conda-forge"
    if name == "pixi" and package["kind"] != "conda":
        return "UNKNOWN", "PyPI pixi is not the Pixi executable"
    safe = version_at_least(package["version"], MINIMUMS[name])
    if safe is None:
        return "UNKNOWN", "not a stable numeric release; verify manually"
    return ("OK" if safe else "AFFECTED"), ""


def pixi(manifest, *args):
    command = ["pixi", *args, "--manifest-path", str(manifest)]
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"{' '.join(command)} failed:\n{detail}")
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "workspace", nargs="?", type=Path, default=Path("."),
        help="Pixi workspace directory or manifest file (default: current directory)",
    )
    args = parser.parse_args()
    print(
        "Checking locked versions only, not installed certificate files or OS/custom CA stores.",
        file=sys.stderr,
    )
    try:
        info = pixi(args.workspace.resolve(), "info", "--json")
        if version_at_least(info["version"], MINIMUMS["pixi"]) is not True:
            raise RuntimeError(f"Pixi >= {MINIMUMS['pixi']} (stable) is required; found {info['version']}")
        project = info.get("project_info")
        if project is None:
            raise RuntimeError("Pixi could not load the workspace; inspect its requires-pixi policy")
        manifest = Path(project["manifest_path"])
        if not manifest.with_name("pixi.lock").is_file():
            raise RuntimeError(f"{manifest}: pixi.lock is required; no resolution was attempted")
        failed = False
        found = False
        for environment in sorted(info["environments_info"], key=lambda entry: entry["name"]):
            name = environment["name"]
            for platform in sorted(entry["name"] for entry in environment["platforms"]):
                packages = pixi(
                    manifest, "list", "--frozen", "--no-install", "--json",
                    "--environment", name, "--platform", platform, PACKAGE_FILTER,
                )
                for package in sorted(packages, key=lambda row: (row["name"].lower(), row["kind"])):
                    found = True
                    package_name = package["name"].lower()
                    state, reason = package_status(package)
                    failed |= state != "OK"
                    detail = f"; {reason}" if reason else ""
                    print(f"  {name}/{platform}: {package_name} {package['version']} "
                          f"({package['kind']}, {state}; minimum {MINIMUMS[package_name]}{detail})")
        if not found:
            print("  No incident packages in this lockfile")
        return 1 if failed else 0
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
