"""Create immutable release metadata from values supplied by Jenkins."""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path

SEMANTIC_VERSION = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--build-number", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--image", required=True)
    args = parser.parse_args()

    if not SEMANTIC_VERSION.fullmatch(args.version):
        raise SystemExit("VERSION must use MAJOR.MINOR.PATCH semantic versioning")

    manifest = {
        "version": args.version,
        "build_number": args.build_number,
        "commit": args.commit,
        "image": args.image,
        "created_at": datetime.now(UTC).isoformat(),
    }
    Path("release-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
