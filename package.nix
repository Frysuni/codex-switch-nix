{
  lib,
  stdenvNoCC,
  fetchurl,
  version,
  source,
}:

stdenvNoCC.mkDerivation {
  pname = "codex-switch";
  inherit version;

  src = fetchurl {
    inherit (source) url hash;
  };

  # Upstream release archives contain the binary at the archive root together
  # with license/notice files, rather than a single enclosing directory.
  sourceRoot = ".";

  dontBuild = true;
  # Preserve the attested upstream executable byte-for-byte.
  dontStrip = true;
  dontPatchELF = true;

  installPhase = ''
    runHook preInstall

    install -Dm755 codex-switch "$out/bin/codex-switch"

    if [ -f LICENSE ]; then
      install -Dm644 LICENSE "$out/share/licenses/codex-switch/LICENSE"
    fi

    if [ -d THIRD-PARTY-LICENSES ]; then
      mkdir -p "$out/share/licenses/codex-switch/THIRD-PARTY-LICENSES"
      cp -R THIRD-PARTY-LICENSES/. "$out/share/licenses/codex-switch/THIRD-PARTY-LICENSES/"
    fi

    runHook postInstall
  '';

  meta = {
    description = "Multi-account profile manager for OpenAI Codex CLI";
    homepage = "https://github.com/xjoker/codex-switch";
    changelog = "https://github.com/xjoker/codex-switch/blob/master/docs/CHANGELOG.md";
    license = lib.licenses.mit;
    mainProgram = "codex-switch";
    platforms = [
      "x86_64-linux"
      "aarch64-linux"
    ];
    sourceProvenance = with lib.sourceTypes; [ binaryNativeCode ];
  };
}
