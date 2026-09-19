"""Run the Streamlit front end with the project Python runtime."""

import subprocess
import sys


if __name__ == "__main__":
    raise SystemExit(subprocess.call([sys.executable, "-m", "streamlit", "run", "frontend/streamlit_app.py", "--server.headless", "true", "--server.port", "8501"]))
