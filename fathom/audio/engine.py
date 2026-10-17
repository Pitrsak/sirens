"""Zvukový engine: spuštění pyo serveru a propojení syntezátoru s analýzou."""

from pyo import Server

from fathom.audio.analyzer import Analyzer
from fathom.audio.synth import Synth


class AudioEngine:
    def __init__(self, sample_rate: int = 44100, buffer_size: int = 512):
        # duplex=0: nepotřebujeme mikrofon, jen výstup (méně problémů se zařízeními).
        self.server = Server(sr=sample_rate, nchnls=2, buffersize=buffer_size, duplex=0)
        self.server.boot()
        self.server.start()
        # pyo objekty lze vytvářet až po boot() serveru.
        self.synth = Synth()
        self.analyzer = Analyzer(self.synth.output)

    def close(self):
        self.server.stop()
        self.server.shutdown()
