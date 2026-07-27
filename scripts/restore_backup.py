from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.backup import restore_backup, verify_backup


def main() -> None:
    parser = argparse.ArgumentParser(description='Verify and restore an AutoPassport backup archive.')
    parser.add_argument('archive', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--overwrite', action='store_true', help='Replace a non-empty destination directory.')
    parser.add_argument('--verify-only', action='store_true', help='Only verify the backup archive.')
    args = parser.parse_args()

    if args.verify_only:
        result = verify_backup(args.archive)
        print(result)
        raise SystemExit(0 if result.get('verified') else 2)

    result = restore_backup(args.archive, args.destination, overwrite=args.overwrite)
    print(f"Restored: {result['restored']}")
    print(f"Target: {result['target_dir']}")
    print(f"Database exists: {result['database_exists']}")
    print(f"Storage files: {result['storage_files']}")


if __name__ == '__main__':
    main()
