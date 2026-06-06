{
  description = "Flask development shell with requirements.txt";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.05";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        python = pkgs.python311;
      in
      {
        # devShell for this system
        devShells = {
          default = pkgs.mkShell {
            buildInputs = [
              python
              pkgs.python311Packages.virtualenv
              pkgs.git
            ];

            # optional: set PYTHONPATH to prefer .venv Python if you want tools outside venv
            shellHook = ''
              # create venv if missing
              if [ ! -d .venv ]; then
                echo "Creating .venv..."
                python -m venv .venv
              fi

              # activate
              . .venv/bin/activate

              # upgrade pip and install requirements once per shell enter
              if [ -f requirements.txt ]; then
                echo "Installing/Updating Python deps from requirements.txt..."
                pip install --upgrade pip setuptools wheel
                pip install -r requirements.txt || true
              fi

              echo "Flask dev shell ready (Python: $(python --version))."
            '';
          };
        };
      }
    );
}
