"""Vstupní bod aplikace: `python -m fathom` nebo `python main.py`."""

from fathom import __version__


def main() -> None:
    print(f"Fathom {__version__}")


if __name__ == "__main__":
    main()
