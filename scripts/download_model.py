"""Fetch and unzip the small offline Vosk English speech model used for
voice-command recognition. Run once after `pip install -r requirements.txt`.
"""

import sys
import zipfile
from pathlib import Path
from urllib.request import urlretrieve

ROOT_DIR = Path(__file__).resolve().parent.parent
MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
MODEL_DIR = ROOT_DIR / "models"
ZIP_PATH = MODEL_DIR / "vosk-model-small-en-us-0.15.zip"
EXTRACTED_DIR = MODEL_DIR / "vosk-model-small-en-us-0.15"


def _progress_hook(block_num, block_size, total_size):
    done = block_num * block_size
    pct = min(100, done * 100 // total_size) if total_size > 0 else 0
    sys.stdout.write(f"\rDownloading model... {pct}% ({done // 1024 // 1024} MB)")
    sys.stdout.flush()


def main():
    if EXTRACTED_DIR.exists():
        print(f"Model already present at {EXTRACTED_DIR}, nothing to do.")
        return

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Fetching {MODEL_URL}")
    urlretrieve(MODEL_URL, ZIP_PATH, reporthook=_progress_hook)
    print("\nExtracting...")
    with zipfile.ZipFile(ZIP_PATH) as z:
        z.extractall(MODEL_DIR)
    ZIP_PATH.unlink()
    print(f"Model ready at {EXTRACTED_DIR}")


if __name__ == "__main__":
    main()
