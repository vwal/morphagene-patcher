"""Private reference firmware for optional full-image integration tests.

Never distribute these images. Set MGMOD_REFERENCE_DIR to the retained
Development 8 package, which includes the tested rollback images.
"""
import os
from pathlib import Path


def reference(relative):
    source = Path(__file__).resolve().parents[1]
    candidates = []
    if os.environ.get('MGMOD_REFERENCE_DIR'):
        candidates.append(Path(os.environ['MGMOD_REFERENCE_DIR']))
    candidates += [source.parent, source.parent/'morphagene-dev8-effects']
    for root in candidates:
        path = root/relative
        if path.is_file():
            return path
    raise FileNotFoundError(f'Set MGMOD_REFERENCE_DIR to private reference package containing {relative}')
