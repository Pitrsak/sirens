"""Aplikace využívající dvě vlákna v architektuře producent-konzument. Obě části sdílí data v podobě jedné proměnné shared.
Producent přečte ze standardního vstupu číslo a uloží ho do sdílené proměnné. Konzument (spící vlákno) se každých n sekund probudí a 
ověří, jestli se sdílená proměnná nezměnila. Pokud ano vypíše ji na standardní výstup a uspí se na dalších n sekund. Pokud producent 
má na vstupu záporné číslo, uloží ho, opustí cyklus a čeká na ukončení konzumenta. Ten když najde ve sdílené proměnné záporné číslo, 
vypíše ho na standardní výstup a skončí také a tím i celá aplikace."""

import threading
import time
import logging

shared = 0

def producer():
    global shared
    num = 0
    while num>=0:    
        num = int(input("Main: Enter an integer: "))
        logging.info("Main    : read num %d",num)
        shared = num
        logging.info("Main    : read shared %d",shared)


def consumer(name):
    logging.info("Thread %s: starting", name)
    
    tmp = shared
    data = tmp
    while tmp>=0:
        logging.info("Thread %d: shared %d.", name, shared)
        logging.info("Thread %d: new loop.(%d,%d)",name,tmp,data)
        if tmp!=data:
            logging.info("Thread %d: new data produced: %d", name,tmp)
            data = tmp
        logging.info("Thread %d: sleeping.",name)
        time.sleep(6)
        tmp = shared
    logging.info("Thread %s: finish.", name)

if __name__=="__main__":
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
    logging.info("Main    : before creating thread")
    x = threading.Thread(target=consumer,args=(1,))
    logging.info("Main    : before running thread")
    x.start()
    logging.info("Main    : running producer")
    producer()
    logging.info("Main    : wait for the thread to finish")
    x.join()
    logging.info("Main    : done.")
