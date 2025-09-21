# main.py
"""DrugX - Main entry point for the drug interaction analysis application."""

import os
import subprocess
import sys


def main():
    """Launch the DrugX Streamlit application."""
    frontend_path = os.path.join(os.path.dirname(__file__), "src", "frontend", "app.py")

    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                frontend_path,
                "--server.port",
                "7860",
                "--server.address",
                "0.0.0.0",
                "--server.runOnSave",
                "true",
            ]
        )
    except KeyboardInterrupt:
        print("\nDrugX application stopped.")
    except Exception as e:
        print(f"Error launching DrugX: {e}")


if __name__ == "__main__":
    main()
