import argparse
import sys

from regression import runner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run rv render regression tests.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "list_tests",
        help="Print available regression case names and exit.",
    )

    test_parser = subparsers.add_parser(
        "test",
        help="Render and compare regression cases against golden outputs.",
    )
    test_parser.add_argument(
        "--case",
        action="append",
        dest="cases",
        default=[],
        help="Run only the named regression case. Can be specified multiple times.",
    )
    test_parser.add_argument(
        "--keep-render",
        action="store_true",
        help="Keep temporary render directories for inspection.",
    )

    regen_parser = subparsers.add_parser(
        "regenerate",
        help="Regenerate golden outputs from current renders.",
    )
    regen_parser.add_argument(
        "--case",
        action="append",
        dest="cases",
        default=[],
        help="Regenerate only the named regression case. Can be specified multiple times.",
    )
    regen_parser.add_argument(
        "--keep-render",
        action="store_true",
        help="Keep temporary render directories for inspection.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv or sys.argv[1:])

    if args.command == "list_tests":
        return runner.main(["--list"])
    if args.command == "test":
        cmd = []
        for case in args.cases:
            cmd.extend(["--case", case])
        if args.keep_render:
            cmd.append("--keep-render")
        return runner.main(cmd)
    if args.command == "regenerate":
        cmd = ["--regen"]
        for case in args.cases:
            cmd.extend(["--case", case])
        if args.keep_render:
            cmd.append("--keep-render")
        return runner.main(cmd)

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
