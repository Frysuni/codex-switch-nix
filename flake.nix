{
  description = "Nix flake for xjoker/codex-switch using official upstream release binaries";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs =
    { self, nixpkgs }:
    let
      sources = builtins.fromJSON (builtins.readFile ./sources.json);
      systems = builtins.attrNames sources.platforms;
      forAllSystems = nixpkgs.lib.genAttrs systems;

      pkgsFor = system: import nixpkgs { inherit system; };

      mkCodexSwitch =
        system:
        let
          pkgs = pkgsFor system;
        in
        pkgs.callPackage ./package.nix {
          inherit (sources) version;
          source = sources.platforms.${system};
        };
    in
    {
      packages = forAllSystems (system: rec {
        codex-switch = mkCodexSwitch system;
        default = codex-switch;
      });

      apps = forAllSystems (system: rec {
        codex-switch = {
          type = "app";
          meta.description = "Run codex-switch";
          program = "${self.packages.${system}.codex-switch}/bin/codex-switch";
        };
        default = codex-switch;
      });

      checks = forAllSystems (system: {
        package = self.packages.${system}.codex-switch;
      });

      formatter = forAllSystems (system: (pkgsFor system).nixfmt);

      overlays.default = final: _prev: {
        codex-switch = final.callPackage ./package.nix {
          inherit (sources) version;
          source =
            sources.platforms.${final.stdenv.hostPlatform.system}
              or (throw "codex-switch: unsupported system ${final.stdenv.hostPlatform.system}");
        };
      };

      nixosModules.default =
        {
          config,
          lib,
          pkgs,
          ...
        }:
        let
          cfg = config.programs.codex-switch;
          system = pkgs.stdenv.hostPlatform.system;
        in
        {
          options.programs.codex-switch = {
            enable = lib.mkEnableOption "codex-switch";

            package = lib.mkOption {
              type = lib.types.package;
              default = self.packages.${system}.codex-switch;
              defaultText = lib.literalExpression "inputs.codex-switch.packages.${pkgs.stdenv.hostPlatform.system}.codex-switch";
              description = "The codex-switch package to install.";
            };
          };

          config = lib.mkIf cfg.enable {
            environment.systemPackages = [ cfg.package ];
          };
        };
    };
}
