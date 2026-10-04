#!/usr/bin/env python3
"""Verify pinned archives against their hashes and the upstream release attestation."""
import hashlib
import json
import subprocess
import tempfile
import urllib.request
from pathlib import Path

from update import PLATFORMS, SOURCES_FILE, VERSION, release_asset_url, sha256_to_sri


def download(url, target):
    digest = hashlib.sha256()
    with urllib.request.urlopen(url, timeout=60) as response, target.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            digest.update(chunk)
            output.write(chunk)
    return sha256_to_sri(digest.hexdigest())


def main():
    data = json.loads(SOURCES_FILE.read_text())
    match = VERSION.fullmatch(data["tag"])
    if not match or match.group(1) != data["version"]:
        raise RuntimeError("inconsistent release version/tag")
    if set(data["platforms"]) != set(PLATFORMS):
        raise RuntimeError("unexpected platform set")
    with tempfile.TemporaryDirectory(prefix="codex-switch-verify-") as directory:
        root = Path(directory)
        bundle = root / "provenance.json"
        url = release_asset_url(
            {"browser_download_url": data["provenance_url"]},
            data["tag"], "codex-switch-build-provenance.json",
        )
        download(url, bundle)
        for system, name in PLATFORMS.items():
            source = data["platforms"][system]
            if source["asset"] != name:
                raise RuntimeError(f"unexpected archive for {system}")
            url = release_asset_url(
                {"browser_download_url": source["url"]}, data["tag"], name,
            )
            archive = root / name
            if download(url, archive) != source["hash"]:
                raise RuntimeError(f"archive checksum mismatch: {name}")
            subprocess.run([
                "gh", "attestation", "verify", str(archive),
                "--bundle", str(bundle), "--repo", "xjoker/codex-switch",
                "--signer-workflow", "xjoker/codex-switch/.github/workflows/release.yml",
                "--source-ref", f"refs/tags/{data['tag']}",
                "--deny-self-hosted-runners",
            ], check=True)


if __name__ == "__main__":
    main()
