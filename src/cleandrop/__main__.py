from __future__ import annotations

import sys

from cleandrop.bootstrap import main as gui_main
from cleandrop.cli import main as cli_main
from cleandrop.worker.worker_main import main as worker_main


def main() -> int:
    if "--worker" in sys.argv:
        sys.argv.remove("--worker")
        return worker_main()
    if len(sys.argv) > 1:
        return cli_main()
    return gui_main()


if __name__ == "__main__":
    raise SystemExit(main())
