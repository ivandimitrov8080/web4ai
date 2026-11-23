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
                buildInputs = old.buildInputs or [ ] ++ [ pkgs.chromium ];
                nativeBuildInputs = old.nativeBuildInputs ++ [ pkgs.makeWrapper ];
                postFixup = old.postFixup or "" + ''
                  wrapProgram $out/bin/web4ai --set CHROMIUM_PATH ${pkgs.chromium}/bin/chromium
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
