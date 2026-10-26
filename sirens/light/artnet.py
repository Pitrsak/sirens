"""Posílání DMX hodnot po síti, protokolem Art-Net.

DMX = 512 kanálů, každej 0..255 (jas jedný barvy, poloha hlavy, ...).
Art-Net je posílá v UDP paketech na port 6454. Paket ArtDmx vypadá takhle:

    "Art-Net\\0"   8 B   identifikace protokolu
    OpCode        2 B   0x5000 = ArtDmx, nižší bajt první (little-endian)
    ProtVer       2 B   verze protokolu 14, vyšší bajt první (big-endian)
    Sequence      1 B   pořadí paketu 1..255, příjemce podle něj pozná starý pakety
    Physical      1 B   číslo fyzickýho portu (nepoužívám, 0)
    SubUni, Net   2 B   číslo universa: nižších 8 bitů, pak vyšších 7 bitů
    Length        2 B   počet kanálů, big-endian
    Data          Length B, hodnoty kanálů

endian je jen pořadí bajtů u čísla, co se nevejde do jednoho bajtu, třeba 512 = 0x0200
je big-endian 02 00 a little-endian 00 02. Art-Net to má fakt takhle napůl, tak pozor.
UDP = pošlu a nečekám na žádný potvrzení, když se paket ztratí, nevadí, za chvíli letí další.
"""

import socket
import struct

PORT = 6454     # Art-Net má pevnej port, na tom poslouchá každej node i konzole


class ArtNetSender:
    def __init__(self):
        # socket = "zásuvka" do sítě, AF_INET = IPv4 adresy,
        # SOCK_DGRAM = UDP (jednotlivý pakety, žádný spojení jako u TCP)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # dovolí posílat i na broadcast adresu (třeba 2.255.255.255 = všem v síti)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sequence = 1       # počítadlo paketů, od 1, protože 0 v Art-Netu znamená "pořadí nesleduj"

    def send(self, ip: str, universe: int, channels: list[int]):
        """Pošle hodnoty kanálů (0..255) do daného universa.

        Když síť zlobí, vyhodí OSError (ten chytá light_page).
        """
        data = bytes(channels)      # seznam čísel -> bajty, každý číslo musí bejt 0..255
        # hlavička, struct.pack poskládá čísla do bajtů podle formátu:
        #   "<8sH"     < = little-endian, 8s = 8 bajtů textu, H = 2bajtový číslo (OpCode)
        #   ">HBBBBH"  > = big-endian, H verze, B sequence, B physical, B SubUni, B Net, H délka
        # universe & 0xFF = spodních 8 bitů, (universe >> 8) & 0x7F = dalších 7 bitů
        header = (struct.pack("<8sH", b"Art-Net\0", 0x5000)
                  + struct.pack(">HBBBBH", 14, self.sequence, 0,
                                universe & 0xFF, (universe >> 8) & 0x7F, len(data)))
        self.sock.sendto(header + data, (ip, PORT))      # hlavička + data jako jeden paket na danou IP
        self.sequence = self.sequence % 255 + 1      # 1, 2, ..., 255, 1, ...

    def close(self):
        self.sock.close()
