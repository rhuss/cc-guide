"""Mini Host command line interface (test fixture)."""
import sys

GREETING = "hello"


def main(argv: list[str]) -> int:
    if argv[:1] == ["greet"]:
        print(GREETING)
        return 0
    if argv[:1] == ["version"]:
        print("0.1.0")
        return 0
    print("usage: mini-host greet|version", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
