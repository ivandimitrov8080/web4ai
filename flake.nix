{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    systems.url = "github:nix-systems/default";
    devenv.url = "github:cachix/devenv";
    devenv.inputs.nixpkgs.follows = "nixpkgs";
    treefmt-nix.url = "github:numtide/treefmt-nix";
    pyproject-nix.url = "github:pyproject-nix/pyproject.nix";
    pyproject-nix.inputs.nixpkgs.follows = "nixpkgs";
    uv2nix.url = "github:pyproject-nix/uv2nix";
    uv2nix.inputs.nixpkgs.follows = "nixpkgs";
    pyproject-build-systems.url = "github:pyproject-nix/build-system-pkgs";
    pyproject-build-systems.inputs.nixpkgs.follows = "nixpkgs";
  };
  outputs =
    inputs@{
      nixpkgs,
      systems,
      devenv,
      treefmt-nix,
      ...
    }:
    let
      eachSystem = nixpkgs.lib.genAttrs (import systems);
    in
    {
      packages = eachSystem (
        system:
        let
          pkgs = import nixpkgs {
            inherit system;
          };
        in
        {
          default =
            (inputs.self.devShells.${system}.default.config.languages.python.import ./. { }).overrideAttrs
              (old: {
                buildInputs =
                  old.buildInputs or [ ]
                  ++ (with pkgs; [
                    chromium
                    ripgrep
                  ]);
                nativeBuildInputs = old.nativeBuildInputs ++ [ pkgs.makeWrapper ];
                postInstall = ''
                  mkdir -p $out/src
                  cp ${./src/see.js} $out/src/see.js
                '';
                postFixup = old.postFixup or "" + ''
                  wrapProgram $out/bin/web4ai \
                    --set CRAWL4AI_NO_CLOUD_NOTICE 1 \
                    --set PYDANTIC_AI_NO_BANNER 1 \
                    --set PROJECT_ROOT $out
                '';
              });
        }
      );
      devShells = eachSystem (
        system:
        let
          pkgs = import nixpkgs {
            inherit system;
          };
        in
        {
          default = devenv.lib.mkShell {
            inherit inputs pkgs;
            modules = [
              (
                { config, ... }:
                let
                  web4ai = config.languages.python.import ./. { };
                in
                {
                  devenv.root = "/home/ivand/src/web4ai";
                  languages = {
                    python = {
                      enable = true;
                      uv.enable = true;
                    };
                  };
                  packages = with pkgs; [
                    web4ai
                    ruff
                    playwright
                    visidata
                    chromium
                  ];
                  env = {
                    CHROMIUM_PATH = "${pkgs.chromium}/bin/chromium";
                  };
                }
              )
            ];
          };
        }
      );
      formatter = eachSystem (
        system:
        let
          pkgs = import nixpkgs { inherit system; };
        in
        (treefmt-nix.lib.evalModule pkgs {
          projectRootFile = "flake.nix";
          programs = {
            nixfmt.enable = true;
            prettier.enable = true;
            deadnix.enable = true;
            statix.enable = true;
            ruff.enable = true;
          };
        }).config.build.wrapper
      );
    };
}
