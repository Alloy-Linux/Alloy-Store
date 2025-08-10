{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    apm.url = "github:Alloy-Linux/apm/main";
  };

  outputs = { self, nixpkgs, apm, ... } @ inputs:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs {
        inherit system;
        overlays = [];
      };
    in {
      devShells.${system} = {
        default = pkgs.mkShell {
          packages = [
            apm.packages.${system}.default
            pkgs.python3
            pkgs.python3Packages.pygobject3
            pkgs.pkg-config
            pkgs.cairo
            pkgs.gtk4
            pkgs.libadwaita
            pkgs.jq
          ];

          shellHook = ''
            source .venv/bin/activate
            alias run="python3 app/main.py"
            echo "dev shell loaded"
          '';
        };
      };
    };
}