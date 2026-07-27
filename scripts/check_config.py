#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import ConfigurationError, assert_runtime_config


def main() -> int:
    try:
        config = assert_runtime_config()
    except ConfigurationError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 2

    print(
        json.dumps(
            {
                "status": "ok",
                "environment": config.environment,
                "database_url_configured": bool(config.database_url),
                "storage_path": str(config.storage_path),
                "backup_path": str(config.backup_path),
                "public_base_url": config.public_base_url,
                "cookie_secure": config.cookie_secure,
                "max_upload_bytes": config.max_upload_bytes,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
