"""Jednoduchá komunikace po síti pomocí tzv. socketu. Aplikace se spustí 
s parametrem jako send nebo listen (tedy na dvo různých terminálech nebo počítačích) 
a podle toho poběží jako odesílatel (sender) nebo příjemce (listener). Sender přečte číslo 
ze standardního vstupu a odešle ho příjemci. 
Ten číslo vypíše na standardní výstup. Pokud sender přečte záporné číslo, odešle ho a skončí. 
Pokud listener přijme záporné číslo vypíše ho na standardní výstup a také skončí."""

from socket import *
import sys

PORT = 5000
IPADDRESS = "localhost"
DATALEN=4

def sender():
    host = IPADDRESS
    port = PORT
    sckt = socket(AF_INET, SOCK_DGRAM)

    num = 0
    while num>=0:    
        num = int(input("Enter an integer: "))
        k = num.to_bytes(length=DATALEN,byteorder="big",signed=True)
        sckt.sendto(k, (host, port))


def listener():
    port = PORT
    address = IPADDRESS
    sckt = socket(AF_INET, SOCK_DGRAM)
    sckt.bind((address, port))
    n = 0
    print(f"Listening on {address}:{port}...\n")
    while n>=0:
        try:
            data, addrinfo = sckt.recvfrom(DATALEN)
            print("Received data: ",data)
            n = int.from_bytes(bytes=data,byteorder="big",signed=True)
        except:
            n = -1

        print(f"Decoded: {n}\n")
    print("Done.")


if sys.argv[1]=="send" or sys.argv[1]=="s":
    sender()
elif sys.argv[1]=="listen" or sys.argv[1]=="l":
    listener()
else:
    print("Usage: python soc.py [send|listen|s|l]\n")



    

