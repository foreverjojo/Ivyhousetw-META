{ pkgs, ... }: {
  # IDX configuration for Firebase Studio
  # This enables the project to be opened in Firebase Studio (Google's cloud IDE)
  
  # Channel to use for packages
  channel = "stable-23.11";
  
  # Packages to install (only system-level packages)
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
      # On create, install Python dependencies via pip
      onCreate = {
        install-deps = ''
          python -m pip install --upgrade pip
          pip install -r requirements.txt
        '';
      };
      
      # On start, provide helpful commands
      onStart = {
        info = "echo 'Ivy House Meta Analyzer ready! Run: python main.py'";
      };
    };
    
    # Preview configuration
    previews = {
      enable = true;
      previews = {
        web = {
          # Run Streamlit directly in dev environment (not main.py)
          command = [
            "sh" "-c"
            "pip install -q -r requirements.txt && streamlit run app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true"
          ];
          manager = "web";
          env = {
            PORT = "$PORT";
          };
        };
      };
    };
  };
}
