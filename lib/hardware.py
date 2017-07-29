import time

try:
    import RPi.GPIO as GPIO
    hardware_present = True
except ImportError:
    hardware_present = False


class Radio:
    """ Abstraction class for radio control """
    PIN_PTT = 3
    HOLD_DELAY = 1.0
    STATE_HOLD = 0
    STATE_RELEASED = 1

    def __init__(self, pin_ptt=PIN_PTT):
        self.hold_ts = None
        self.state = Radio.STATE_RELEASED
        if hardware_present:
            self.pin_ptt = pin_ptt
            GPIO.setmode(GPIO.BOARD)
            GPIO.setup(self.pin_ptt, GPIO.OUT, initial=GPIO.HIGH)

    def talk(self):
        if self.state == Radio.STATE_HOLD:
            return

        if hardware_present:
            GPIO.output(self.pin_ptt, GPIO.LOW)

        print("PTT hold")
        self.hold_ts = time.time()
        self.state = Radio.STATE_HOLD

    def is_ready(self):
        if self.hold_ts is None:
            return False
        return (time.time() - self.hold_ts) > Radio.HOLD_DELAY

    def release(self):
        if self.state == Radio.STATE_RELEASED:
            return

        if hardware_present:
            GPIO.output(self.pin_ptt, GPIO.HIGH)

        print("PTT released")
        self.hold_ts = None
        self.state = Radio.STATE_RELEASED
