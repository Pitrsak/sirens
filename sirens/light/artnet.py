"""Odesílání DMX hodnot po síti protokolem Art-Net.

DMX = 512 kanálů, každý 0..255 (jas jedné barvy, poloha hlavy, ...).
Art-Net je posílá v UDP paketech na port 6454. Paket ArtDmx:

    "Art-Net\\0"   8 B   identifikace protokolu
    OpCode        2 B   0x5000 = ArtDmx, nižší bajt první (little-endian)
    ProtVer       2 B   verze protokolu 14, vyšší bajt první (big-endian)
    Sequence      1 B   pořadí paketu 1..255, příjemce podle něj pozná staré pakety
    Physical      1 B   číslo fyzického portu (nepoužíváme, 0)
    SubUni, Net   2 B   číslo universa: nižší 8 bitů, pak vyšších 7 bitů
    Length        2 B   počet kanálů, big-endian
    Data          Length B, hodnoty kanálů
"""

import socket
import struct

PORT = 6454


class ArtNetSender:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # dovolí posílat i na broadcast adresu (např. 2.255.255.255 = všem v síti)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sequence = 1

    def send(self, ip: str, universe: int, channels: list[int]):
        """Pošle hodnoty kanálů (0..255) do daného universa. Chyba sítě vyvolá OSError."""
        data = bytes(channels)
        header = (struct.pack("<8sH", b"Art-Net\0", 0x5000)
                  + struct.pack(">HBBBBH", 14, self.sequence, 0,
                                universe & 0xFF, (universe >> 8) & 0x7F, len(data)))
        self.sock.sendto(header + data, (ip, PORT))
        self.sequence = self.sequence % 255 + 1      # 1, 2, ..., 255, 1, ...

    def close(self):
        self.sock.close()
