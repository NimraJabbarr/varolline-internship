"""Allow ``python -m csvtool``."""

from csvtool.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
