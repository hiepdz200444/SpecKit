import os
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

# keep test artefacts out of the app's data dir
os.environ.setdefault("LRS_DATA_DIR", tempfile.mkdtemp(prefix="lrs-test-"))
