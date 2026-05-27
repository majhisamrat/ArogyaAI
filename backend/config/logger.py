import logging
import os
import sys


os.makedirs("logs", exist_ok=True)

# Create handlers explicitly and ensure UTF-8 encoding for file and console on Windows
handlers = []

file_handler = logging.FileHandler("logs/app.log", encoding="utf-8")
file_handler.setLevel(logging.INFO)
handlers.append(file_handler)

# Use UTF-8 console stream on Windows to avoid UnicodeEncodeError for emoji
if os.name == "nt":
    try:
        console_stream = open("CONOUT$", "w", encoding="utf-8", errors="replace")
        stream_handler = logging.StreamHandler(stream=console_stream)
    except Exception:
        stream_handler = logging.StreamHandler()
else:
    stream_handler = logging.StreamHandler(sys.stdout)

stream_handler.setLevel(logging.INFO)
handlers.append(stream_handler)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=handlers,
)

logger = logging.getLogger("health_assistant")