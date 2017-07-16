try:
    import RPi.GPIO as GPIO
    hardware_present = True
except ImportError:
    hardware_present = False


class Radio:
    """ Abstraction class for radio control """
    PIN_PTT = 3

    def __init__(self, pin_ptt=PIN_PTT):
        if hardware_present:
            self.pin_ptt = pin_ptt
            GPIO.setmode(GPIO.BOARD)
            GPIO.setup(self.pin_ptt, GPIO.OUT, initial=GPIO.HIGH)

    def talk(self):
        if hardware_present:
            GPIO.output(self.pin_ptt, GPIO.LOW)
        print("PTT hold")

    def release(self):
        if hardware_present:
            GPIO.output(self.pin_ptt, GPIO.HIGH)
        print("PTT released")
