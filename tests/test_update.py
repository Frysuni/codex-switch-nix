import copy
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("update", Path(__file__).resolve().parents[1] / "scripts/update.py")
update = importlib.util.module_from_spec(spec)
spec.loader.exec_module(update)


class UpdaterTests(unittest.TestCase):
    def setUp(self):
        self.digest = "a" * 64
        self.tag = "v20261001.5.0"
        self.release = {
            "tag_name": self.tag,
            "published_at": "2026-10-01T06:53:29Z",
            "html_url": f"https://github.com/{update.REPO}/releases/tag/{self.tag}",
            "assets": [],
        }
        for name in [*update.PLATFORMS.values(), *(n + ".sha256" for n in update.PLATFORMS.values()), "codex-switch-build-provenance.json"]:
            self.release["assets"].append({
                "name": name,
                "browser_download_url": f"https://github.com/{update.REPO}/releases/download/{self.tag}/{name}",
                "digest": "sha256:" + self.digest,
            })

    def run_update(self, release):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "sources.json"
            original = '{"tag": "old"}\n'
            target.write_text(original)
            with patch.object(update, "SOURCES_FILE", target), patch.object(update, "get_json", return_value=release), patch.object(update, "get_text", side_effect=lambda url: self.digest + "  " + url.rsplit("/", 1)[1].removesuffix(".sha256")):
                try:
                    update.main()
                except RuntimeError:
                    self.assertEqual(target.read_text(), original)
                    raise
            return json.loads(target.read_text())

    def test_verified_release(self):
        data = self.run_update(self.release)
        self.assertEqual(data["version"], "20261001.5.0")
        self.assertEqual(set(data["platforms"]), set(update.PLATFORMS))
        self.assertEqual(data["platforms"]["x86_64-linux"]["hash"], update.sha256_to_sri(self.digest))

    def test_rejects_invalid_releases_without_writing(self):
        mutations = [
            lambda r: r.update(prerelease=True),
            lambda r: r.update(draft=True),
            lambda r: r.update(tag_name="v1.2.3-rc1"),
            lambda r: r["assets"].pop(),
            lambda r: r["assets"].pop(0),
            lambda r: r["assets"][0].update(digest=None),
            lambda r: r["assets"][0].update(digest="sha256:" + "b" * 64),
            lambda r: r["assets"][0].update(browser_download_url="https://example.com/archive"),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                release = copy.deepcopy(self.release)
                mutation(release)
                with self.assertRaises(RuntimeError):
                    self.run_update(release)

    def test_checksum_filename_and_format(self):
        name = "cs-linux-amd64.tar.gz"
        self.assertEqual(update.parse_sidecar(self.digest + " *" + name, name), self.digest)
        for value in [self.digest, self.digest + " other.tar.gz", "invalid " + name, self.digest + " " + name + "\nextra"]:
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                update.parse_sidecar(value, name)

    def test_token_is_only_sent_to_github_api(self):
        with patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}):
            self.assertEqual(update.request(update.API_URL).get_header("Authorization"), "Bearer test-token")
            for url in ["https://github.com/xjoker/codex-switch/releases/download/test/file", "https://github.evil.example/file", "http://api.github.com/file"]:
                self.assertIsNone(update.request(url).get_header("Authorization"))


if __name__ == "__main__":
    unittest.main()
