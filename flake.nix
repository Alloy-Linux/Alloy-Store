{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    apm.url = "github:Alloy-Linux/apm/main";
    utils.url = "github:numtide/flake-utils";
    nixos-appstream-data = {
      url = "github:korfuri/nixos-appstream-data/flake";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.flake-utils.follows = "utils";
    };
  };

  outputs = { self, nixpkgs, apm, nixos-appstream-data, ... } @ inputs:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs {
        inherit system;
      };

      appstreamPath = "${nixos-appstream-data.packages.${system}.nixos-appstream-data}/share/app-info/xmls/nixos_x86_64_linux.yml.gz";

    in {
      devShells = {
        ${system} = {
          default = pkgs.mkShell {
            buildInputs = [
              apm.packages.${system}.default
              pkgs.python3
              pkgs.python3Packages.pygobject3
              pkgs.pkg-config
              pkgs.cairo
              pkgs.gtk4
              pkgs.libadwaita
              pkgs.jq
              nixos-appstream-data.packages.${system}.nixos-appstream-data
            ];

            shellHook = ''
              export NIXOS_APPSTREAM_DATA="${appstreamPath}"
              source .venv/bin/activate
              alias run="python3 app/main.py"
              echo "dev shell loaded"
            '';
          };
        };
      };
    };
}
