"""Entry point: `python -m fathom` or `fathom`."""

from fathom import __version__


def main() -> None:
    print(f"Fathom {__version__}")


if __name__ == "__main__":
    main()
