# codex-switch-nix

[![CI](https://github.com/Frysuni/codex-switch-nix/actions/workflows/ci.yml/badge.svg)](https://github.com/Frysuni/codex-switch-nix/actions/workflows/ci.yml)

Nix flake for [xjoker/codex-switch](https://github.com/xjoker/codex-switch).

This repository packages the **official upstream release binaries** instead of rebuilding the Rust project. The package currently supports `x86_64-linux` and `aarch64-linux`.

## Quick run

```bash
nix run github:Frysuni/codex-switch-nix
```

Or run a command directly:

```bash
nix run github:Frysuni/codex-switch-nix -- tui
nix run github:Frysuni/codex-switch-nix -- doctor
```

## NixOS flake input

```nix
{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

    codex-switch = {
      url = "github:Frysuni/codex-switch-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { nixpkgs, codex-switch, ... }: {
    nixosConfigurations.my-host = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      modules = [
        codex-switch.nixosModules.default
        {
          programs.codex-switch.enable = true;
        }
      ];
    };
  };
}
```

You can also use the package directly:

```nix
environment.systemPackages = [
  inputs.codex-switch.packages.${pkgs.stdenv.hostPlatform.system}.default
];
```

For Home Manager:

```nix
home.packages = [
  inputs.codex-switch.packages.${pkgs.stdenv.hostPlatform.system}.default
];
```

## Overlay

```nix
nixpkgs.overlays = [ inputs.codex-switch.overlays.default ];

environment.systemPackages = [ pkgs.codex-switch ];
```

## Updates

The repository is designed to maintain itself:

- `.github/workflows/update.yml` checks the latest **stable** upstream release every 4 hours.
- `scripts/update.py` requires both official Linux assets and their `.sha256` sidecars.
- The updater cross-checks the checksum from the sidecar against GitHub's release-asset digest and converts it to a Nix SRI hash.
- Every CI run and maintenance candidate verifies both archive hashes and the upstream GitHub attestation, requiring the release tag, `release.yml` signer and GitHub-hosted runners.
- The updated package must pass `nix flake check`, build and report the exact expected version on native x86_64 and ARM runners, and install through the NixOS module.
- `.github/workflows/update-nixpkgs.yml` refreshes the pinned `nixpkgs` lock weekly using the same validation.
- Maintenance publishes the exact files validated by both runners. Failed checks or concurrent changes to `main` prevent publication.
- Manual dispatch supports `force_check` to exercise both platforms and the artifact handoff even when the pinned metadata is already current.
- All maintenance commits are made by `github-actions[bot]`; no PAT or external updater service is required.

`codex-switch self-update` should not be used for a Nix-managed installation. The executable lives in the immutable Nix store; update this flake input / lock and rebuild NixOS instead.

[GitHub schedules](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule) can be delayed, and scheduled workflows in inactive public repositories can be disabled after 60 days. Check the Actions page if updates stop; both maintenance workflows also support manual dispatch.

## Development and initial publication

```bash
nix shell nixpkgs#python3 nixpkgs#gh --command bash
python3 -m unittest discover -s tests -v
python3 scripts/verify.py
./scripts/check.sh
```

To create and publish the repository using an authenticated GitHub CLI:

```bash
nix shell nixpkgs#gh nixpkgs#git nixpkgs#python3 --command ./bootstrap.sh
```

The bootstrap validates the package and provenance before committing or pushing. The packaging code is MIT licensed; upstream binaries retain their upstream license.

## Source of truth

Package metadata lives in `sources.json`. It contains the exact upstream release URLs and fixed-output hashes used by Nix. `package.nix` never downloads from mirrors or third-party binary hosts.

## Upstream

- Project: <https://github.com/xjoker/codex-switch>
- Releases: <https://github.com/xjoker/codex-switch/releases>
- License: MIT
