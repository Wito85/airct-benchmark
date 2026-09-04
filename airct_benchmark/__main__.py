"""Allow ``python -m airct_benchmark <mode> ...`` as a synonym of ``python -m airct_benchmark.run``."""

import sys

from .run import main

if __name__ == "__main__":
    sys.exit(main())
