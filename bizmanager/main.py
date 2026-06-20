#!/usr/bin/env python3
"""Backward-compatible launcher for the Streamlit application."""

import os
import sys
from pathlib import Path


def main():
    app_path = Path(__file__).with_name("streamlit_app.py")
    os.execv(
        sys.executable,
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(app_path),
        ],
    )


if __name__ == "__main__":
    main()
