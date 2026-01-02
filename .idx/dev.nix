{ pkgs, ... }: {
  # IDX configuration for Firebase Studio
  # This enables the project to be opened in Firebase Studio (Google's cloud IDE)
  
  # Channel to use for packages
  channel = "stable-23.11";
  
  # Packages to install
  packages = [
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.git
    pkgs.curl
    pkgs.gcc
  ];
  
  # IDX workspace configuration
  idx = {
    # Extensions to install
    extensions = [
      "ms-python.python"
      "ms-python.vscode-pylance"
    ];
    
    # Workspace settings
    workspace = {
      # On create, install dependencies
      onCreate = {
        install-deps = "pip install -r requirements.txt || pip install uv && uv pip install --system -r pyproject.toml";
      };
      
      # On start, provide helpful commands
      onStart = {
        info = "echo 'Ivy House Meta Analyzer ready!'";
      };
    };
    
    # Preview configuration
    previews = {
      enable = true;
      previews = {
        web = {
          command = ["python" "main.py"];
          manager = "web";
          env = {
            PORT = "$PORT";
          };
        };
      };
    };
  };
}
