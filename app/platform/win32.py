
"""Windows platform-specific functionality."""

import os

def open_path(path):
    os.startfile(path)  # noqa: S606 - intended on Windows