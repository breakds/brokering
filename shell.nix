let pkgs = import <nixpkgs> {
      config.allowUnfree = true;
    };

    python = pkgs.python3.withPackages (python-packages: with python-packages; [
      setuptools
      click
      flask
      psutil
      pyyaml
      twisted
    ]);

in pkgs.mkShell rec {
  name = "pyd";
  buildInputs = with pkgs; [ python sqlitebrowser parted ];
  shellHook = ''
    export PS1="$(echo -e '\uf3e2') {\[$(tput sgr0)\]\[\033[38;5;228m\]\w\[$(tput sgr0)\]\[\033[38;5;15m\]} (${name}) \\$ \[$(tput sgr0)\]"
  '';
}
