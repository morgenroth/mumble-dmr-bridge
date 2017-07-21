#!/usr/bin/env python3

from audio import MumbleBridge
import time


def main():
    b = MumbleBridge("mumble.event.formulastudent.de", 64838, "BridgeBot")
    b.connect()

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass

    #b.disconnect()

if __name__ == "__main__":
    main()
