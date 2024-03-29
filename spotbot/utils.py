from datetime import datetime


def set_us_increment(increment: int) -> None:
    """Set µs incrment"""
    global current_us_increment
    current_us_increment = increment


def set_angle_increment(increment: float) -> None:
    """Set ∠ incrment"""
    global current_angle_increment
    current_angle_increment = increment


class Utils(object):
    def __init__(self, parent):
        self.parent = parent

    def get_us_increment(self) -> str:
        """Get current µs incrment as a str"""
        return "{:>4}".format(str(self.parent.us_increment))

    def get_angle_increment(self) -> str:
        """Get current µs incrment as a str"""
        return "{:>5}".format(str(self.parent.angle_increment))

    def is_relay_on_off(self) -> str:
        if self.parent.relay.is_active() is True:
            return "[r]On[/r]"
        else:
            return "Off"

    def get_multi_select(self) -> str:
        if self.parent.body.multi_select is True:
            return "[r]On[/r]"
        else:
            return "Off"

    def a_to_us(servo: dict, angle: float) -> int:
        return 1502

    def status_clock(self) -> str:
        return f"{datetime.now().time().strftime('%X')}"
