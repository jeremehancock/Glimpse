"""Make `scripts/` importable by the tests.

The fetchers and the config generator are scripts the container invokes by path,
not an installed package — so there is no distribution to `pip install -e`, and
adding one would mean a build step the runtime image does not want. Putting the
directory on the path here keeps the test imports plain and top-level.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))
