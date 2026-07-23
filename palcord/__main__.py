"""python -m palcord 用エントリ。"""

from __future__ import annotations

import sys

from palcord.main import main

# パッケージとして起動されたときの入口
if __name__ == "__main__":
    sys.exit(main())
