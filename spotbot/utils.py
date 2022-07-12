from datetime import datetime

# def set_us_increment(increment: int) -> None:
#     """Set µs incrment"""
#     global current_us_increment
#     current_us_increment = increment


# def set_angle_increment(increment: float) -> None:
#     """Set ∠ incrment"""
#     global current_angle_increment
#     current_angle_increment = increment


class Utils(object):
    def __init__(self, parent):
        self.parent = parent

    def get_us_increment(self) -> str:
        """Get current µs incrment as a str"""
        return "{:>6}".format(str(self.parent.us_increment))

    def get_angle_increment(self) -> str:
        """Get current µs incrment as a str"""
        return "{:>5}".format(str(self.parent.angle_increment))

    def is_relay_on_off(self) -> str:
        if self.parent.relay.is_active() is True:
            return "[r]On[/r]"
        else:
            return "Off"

    def refresh_servo_data(self, servoletter: str) -> None:
        servoconfig = self.parent.servo_config[servoletter]
        self.parent.servo_data[servoletter] = (
            servoletter,
            servoconfig["description"],
            servoconfig["designation"],
            # str(Utils.a_to_us(servo, servo["home_angle"])),
            str(self.parent.servo_ctl.get_position_us(servoconfig["position"])),
            str(servoconfig["home_angle"]),
        )
        self.parent.body.update(self.parent.servo_data)
        self.parent.body.refresh()

    def a_to_us(servo: dict, angle: float) -> int:
        return 1502

    def status_clock(self) -> str:
        return f"{datetime.now().time().strftime('%X')}"
