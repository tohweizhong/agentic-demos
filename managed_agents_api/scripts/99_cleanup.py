"""Step 99: delete the demo resources.

The script deletes every agent whose ID starts with `demo-`. It asks before it
deletes. Add `--bucket` to also delete the demo bucket and its files.

Usage:
    python scripts/99_cleanup.py            # Agents only. Asks first.
    python scripts/99_cleanup.py --bucket   # Agents and the bucket. Asks two times.
    python scripts/99_cleanup.py --bucket --skills   # Also the registry skill.
    python scripts/99_cleanup.py --bucket --yes   # No questions.
"""

from __future__ import annotations

import argparse
import sys

from rich.console import Console

from managed_agents_demo import cleanup, client, config, interact_demo, storage


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Delete the demo agents and the demo bucket.")
    parser.add_argument("--bucket", action="store_true", help="Also delete the demo bucket.")
    parser.add_argument(
        "--skills", action="store_true", help="Also delete the Skill Registry skill."
    )
    parser.add_argument("--yes", action="store_true", help="Do not ask for confirmation.")
    args = parser.parse_args(argv)

    console = Console()
    try:
        settings = config.load()
    except config.ConfigError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1
    console.print(f"Project: {settings.project}  Location: {settings.location}")
    rest = client.RestClient(settings)
    sdk = client.make_genai_client(settings)
    storage_client = storage.make_storage_client(settings.project) if args.bucket else None
    return cleanup.run(
        rest,
        sdk,
        storage_client,
        console,
        settings,
        yes=args.yes,
        delete_bucket=args.bucket,
        delete_skills=args.skills,
        state_path=interact_demo.STATE_PATH,
    )


if __name__ == "__main__":
    sys.exit(main())
