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
      "alefragnani.project-manager"
      "bierner.color-info"
      "chouzz.vscode-better-align"
      "christian-kohler.path-intellisense"
      "dbaeumer.vscode-eslint"
      "eamodio.gitlens"
      "emanuelebartolesi.vscode-copilot-insights"
      "esbenp.prettier-vscode"
      "github.copilot"
      "github.copilot-chat"
      "github.vscode-github-actions"
      "github.vscode-pull-request-github"
      "gruntfuggly.todo-tree"
      "gxl.git-graph-3"
      "johnpapa.vscode-peacock"
      "louiswt.regexp-preview"
      "mechatroner.rainbow-csv"
      "ms-azuretools.vscode-containers"
      "ms-python.autopep8"
      "ms-python.debugpy"
      "ms-python.python"
      "ms-python.vscode-pylance"
      "ms-python.vscode-python-envs"
      "oderwat.indent-rainbow"
      "openai.chatgpt"
      "rangav.vscode-thunder-client"
      "ritwickdey.liveserver"
      "streetsidesoftware.code-spell-checker"
      "usernamehw.errorlens"
      "vscode-icons-team.vscode-icons"
      "yzhang.markdown-all-in-one"
      "sst-dev.opencode"
      "ivyhouse-local.ivyhouse-terminal-injector"
      "ivyhouse-local.ivyhouse-terminal-monitor"
      "ivyhouse-local.ivyhouse-terminal-orchestrator"
    ];

    # Workspace settings
    workspace = {
      # On create, create venv and install dependencies
      onCreate = {
        install-deps = ''
          python -m venv .venv
          source .venv/bin/activate
          pip install --upgrade pip
          pip install -r requirements.txt -r requirements-dev.txt
        '';
      };

      # On start, provide helpful commands
      onStart = {
        info = "echo 'Ivy House Meta Analyzer ready! Run: source .venv/bin/activate && python main.py'";
      };
    };

    # Preview configuration
    previews = {
      enable = true;
      previews = {
        web = {
          # Run Streamlit using the virtual environment
          command = [
            "sh" "-c"
            "if [ ! -d .venv ]; then python -m venv .venv; fi && source .venv/bin/activate && pip install -q -r requirements.txt && streamlit run app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true --server.enableCORS=false --server.enableXsrfProtection=false"
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
