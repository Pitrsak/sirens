"""Spouštěcí soubor, tohle se pouští (python main.py).

sám nic nedělá, jen zavolá main() ze sirens/__main__.py, kde se to celý rozjede.
"""

from sirens.__main__ import main

# platí jen když se soubor pustí přímo, při importu odjinud se nic nespustí
if __name__ == "__main__":
    main()
