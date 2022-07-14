import RPi.GPIO as GPIO


class Relay(object):
    def __init__(self, gpio: int, active_high: bool) -> None:
        self.gpio = gpio
        self.active_high = active_high

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.gpio, GPIO.OUT)

        self.off()

    def on(self) -> None:
        if self.active_high is True:
            GPIO.output(self.gpio, GPIO.HIGH)
        else:
            GPIO.output(self.gpio, GPIO.LOW)
        self.active = True

    def off(self) -> None:
        if self.active_high is True:
            GPIO.output(self.gpio, GPIO.LOW)
        else:
            GPIO.output(self.gpio, GPIO.HIGH)
        self.active = False

    def toggle(self) -> None:
        if self.active is True:
            self.off()
        else:
            self.on()

    def is_active(self) -> bool:
        return self.active

    def is_on_off(self) -> str:
        if self.active is True:
            return "On"
        else:
            return "Off"

    def close(self) -> None:
        self.open = False
        GPIO.cleanup()

    def __del__(self) -> None:
        """Catchall cleanup in case the object gets collected"""
        if self.open is True:
            GPIO.cleanup()
