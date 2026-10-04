#!/usr/bin/env python3
"""Update sources.json to the latest stable xjoker/codex-switch release.

The updater deliberately consumes only official GitHub release metadata and
cross-checks every asset digest against the release's .sha256 sidecar before
writing Nix SRI hashes.
"""

from __future__ import annotations

import base64
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPO = "xjoker/codex-switch"
API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
ROOT = Path(__file__).resolve().parents[1]
SOURCES_FILE = ROOT / "sources.json"

PLATFORMS = {
    "x86_64-linux": "cs-linux-amd64.tar.gz",
    "aarch64-linux": "cs-linux-arm64.tar.gz",
}

HEX_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
VERSION = re.compile(r"^v([0-9]+(?:\.[0-9]+){2})$")


def request(url: str) -> urllib.request.Request:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Frysuni/codex-switch-nix updater",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token and urllib.parse.urlparse(url).netloc == "api.github.com" and url.startswith("https://"):
        headers["Authorization"] = f"Bearer {token}"
    return urllib.request.Request(url, headers=headers)


def get_json(url: str):
    with urllib.request.urlopen(request(url), timeout=30) as response:
        return json.load(response)


def get_text(url: str) -> str:
    with urllib.request.urlopen(request(url), timeout=30) as response:
        return response.read().decode("utf-8")


def sha256_to_sri(hex_digest: str) -> str:
    raw = bytes.fromhex(hex_digest)
    return "sha256-" + base64.b64encode(raw).decode("ascii")


def release_asset_url(asset: dict, tag: str, name: str) -> str:
    expected = f"https://github.com/{REPO}/releases/download/{tag}/{name}"
    if asset.get("browser_download_url") != expected:
        raise RuntimeError(f"unexpected download URL for {name}")
    return expected


def parse_sidecar(text: str, expected_asset: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) != 1:
        raise RuntimeError(f"invalid checksum sidecar for {expected_asset}: expected one line")

    parts = lines[0].split()
    if len(parts) != 2:
        raise RuntimeError(f"invalid checksum sidecar for {expected_asset}: expected hash and filename")

    digest, filename = parts
    filename = filename.removeprefix("*")
    if filename != expected_asset or not HEX_SHA256.fullmatch(digest):
        raise RuntimeError(f"invalid checksum sidecar for {expected_asset}")

    return digest.lower()


def main() -> int:
    release = get_json(API_URL)

    if release.get("draft") or release.get("prerelease"):
        raise RuntimeError("GitHub latest release unexpectedly points to a draft/prerelease")

    tag = release.get("tag_name", "")
    match = VERSION.fullmatch(tag)
    if not match:
        raise RuntimeError(f"unexpected stable release tag: {tag!r}")
    version = match.group(1)

    assets = {asset["name"]: asset for asset in release.get("assets", [])}
    platforms = {}

    for system, asset_name in PLATFORMS.items():
        asset = assets.get(asset_name)
        if asset is None:
            raise RuntimeError(f"release {tag} does not contain {asset_name}")

        download_url = release_asset_url(asset, tag, asset_name)
        sidecar_name = asset_name + ".sha256"
        sidecar = assets.get(sidecar_name)
        if sidecar is None:
            raise RuntimeError(f"release {tag} does not contain {sidecar_name}")

        sidecar_digest = parse_sidecar(get_text(release_asset_url(sidecar, tag, sidecar_name)), asset_name)

        api_digest = asset.get("digest")
        if not api_digest:
            raise RuntimeError(f"missing GitHub SHA-256 digest for {asset_name}")
        if api_digest:
            if not api_digest.startswith("sha256:"):
                raise RuntimeError(f"unexpected GitHub digest format for {asset_name}: {api_digest}")
            api_hex = api_digest.removeprefix("sha256:").lower()
            if not HEX_SHA256.fullmatch(api_hex):
                raise RuntimeError(f"invalid GitHub SHA-256 digest for {asset_name}")
            if api_hex != sidecar_digest:
                raise RuntimeError(
                    f"checksum disagreement for {asset_name}: GitHub API={api_hex}, sidecar={sidecar_digest}"
                )

        platforms[system] = {
            "asset": asset_name,
            "url": download_url,
            "hash": sha256_to_sri(sidecar_digest),
        }

    provenance = assets.get("codex-switch-build-provenance.json")
    if provenance is None:
        raise RuntimeError(f"release {tag} does not contain codex-switch-build-provenance.json")

    new_data = {
        "version": version,
        "tag": tag,
        "published_at": release.get("published_at"),
        "release_url": release.get("html_url"),
        "provenance_url": release_asset_url(provenance, tag, "codex-switch-build-provenance.json"),
        "platforms": dict(sorted(platforms.items())),
    }

    old_data = None
    if SOURCES_FILE.exists():
        old_data = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))

    if old_data == new_data:
        print(f"sources.json is already current: {tag}")
        return 0

    SOURCES_FILE.write_text(json.dumps(new_data, indent=2) + "\n", encoding="utf-8")
    old_version = old_data.get("tag", "<none>") if old_data else "<none>"
    print(f"updated sources.json: {old_version} -> {tag}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 - fail closed with a readable CI message
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
