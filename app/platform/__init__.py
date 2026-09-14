"""OCR screen-capture transcription tool (tray app)."""

#Switch the import statement used based on whether the OS is Windows, Mac, or Linux.
import sys

if sys.platform == "win32":
    from .win32 import open_path
elif sys.platform == "darwin":
    from .mac import open_path
else:
    from .linux import open_path