import sys
import time

def main():
    print("=" * 50)
    print("Testing Multimedia 1 (MM1) Environment Setup")
    print("=" * 50)
    print(f"Python interpreter: {sys.executable}")
    print(f"Python version:     {sys.version.split()[0]}")
    print("-" * 50)

    # 1. OpenCV
    try:
        import cv2
        print(f"[OK] OpenCV (cv2) version: {cv2.__version__}")
    except ImportError as e:
        print(f"[FAIL] OpenCV import error: {e}")

    # 2. wxPython
    try:
        import wx
        print(f"[OK] wxPython version:     {wx.__version__}")
    except ImportError as e:
        print(f"[FAIL] wxPython import error: {e}")

    # 3. Pyo
    try:
        import pyo
        print(f"[OK] pyo version:          {pyo.getVersion()}")
        print("\nTesting Pyo audio server (booting server)...")
        s = pyo.Server()
        s.boot()
        print("[OK] Pyo audio server booted successfully!")
        
        # Play a quick test tone (440Hz sine wave for 0.5 seconds) if executed directly
        if "--sound" in sys.argv:
            print("Playing 440 Hz test sine tone for 1 second...")
            s.start()
            tone = pyo.Sine(freq=440, mul=0.2).out()
            time.sleep(1.0)
            tone.stop()
            s.stop()
            print("[OK] Tone playback finished!")
        else:
            print("(To test tone output with sound, run with '--sound')")
            s.stop()
        s.shutdown()
    except Exception as e:
        print(f"[FAIL] pyo error: {e}")

    print("-" * 50)
    print("Setup verification complete!")
    print("=" * 50)

if __name__ == "__main__":
    main()
