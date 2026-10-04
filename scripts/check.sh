#!/usr/bin/env bash
set -euo pipefail
nix flake check --print-build-logs
nix build .#codex-switch --print-build-logs
expected="$(python3 -c 'import json; print(json.load(open("sources.json"))["version"])')"
actual="$(./result/bin/codex-switch --version)"
echo "$actual"
archive="$(nix eval --raw .#codex-switch.src.outPath)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
tar -xzf "$archive" -C "$tmp"
cmp "$tmp/codex-switch" ./result/bin/codex-switch
# Require an exact version token, rather than a substring of another version.
ACTUAL_VERSION="$actual" EXPECTED_VERSION="$expected" python3 - <<'PY'
import os, re
assert os.environ["EXPECTED_VERSION"] in re.findall(r"(?<![\w.])\d+(?:\.\d+){2}(?![\w.])", os.environ["ACTUAL_VERSION"]), "unexpected binary version"
PY
# Evaluate the enabled NixOS module and its installed package.
# shellcheck disable=SC2016
nix eval --impure --json --expr '
let
  flake = builtins.getFlake (toString ./.);
  system = builtins.currentSystem;
  os = flake.inputs.nixpkgs.lib.nixosSystem {
    inherit system;
    modules = [ flake.nixosModules.default { programs.codex-switch.enable = true; system.stateVersion = "26.05"; } ];
  };
in builtins.any (p: p == flake.packages.${system}.default) os.config.environment.systemPackages
' | python3 -c 'import json, sys; assert json.load(sys.stdin), "NixOS module does not install the package"'
