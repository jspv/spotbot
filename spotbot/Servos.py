import re
from typing import Any


class Servo(object):
    MAX_HIGH_US = 3000
    MAX_LOW_US = 300
    MAX_HIGH_A = 270
    MAX_LOW_A = 0
    MAX_CHANNELS = 18

    # Servo controller to be provided externally via this class attribute.
    servo_ctl = None

    def __init__(
        self,
        lettermap: str,
        channel: int,
        description: str,
        designation: str = "",
        high_us: int = 3000,
        low_us: int = 300,
        high_pos: str = "high",
        high_angle: float = 180.0,
        low_angle: float = 0.0,
        home_angle: float = 90.0,
        config: dict = None,
    ) -> None:
        if re.match(r"^[A-R]$", lettermap):
            self.lettermap = lettermap
        else:
            raise ValueError("Lettermap needs to be A thorough R")

        if channel >= 0 and channel < 18:
            self.channel = channel
        else:
            raise ValueError("Channel needs to be between 0 and 17")

        if low_us >= self.MAX_LOW_US or low_us <= self.MAX_HIGH_US:
            self.low_us = low_us
        else:
            raise ValueError(
                f"low_us needs to be between {self.MAX_LOW_US} and {self.MAX_HIGH_US}"
            )

        if high_us >= self.MAX_LOW_US or high_us <= self.MAX_HIGH_US:
            self.high_us = high_us
        else:
            raise ValueError(
                f"high_us needs to be between {self.MAX_LOW_US} and {self.MAX_HIGH_US}"
            )

        if low_angle >= self.MAX_LOW_A and low_angle <= self.MAX_HIGH_A:
            self.low_angle = low_angle
        else:
            raise ValueError(
                f"low_angle needs to be between {self.MAX_LOW_A} and {self.MAX_HIGH_A}"
            )

        if high_angle >= self.MAX_LOW_A and low_angle <= self.MAX_HIGH_A:
            self.high_angle = high_angle
        else:
            raise ValueError(
                f"high_angle needs to be between {self.MAX_LOW_A} and {self.MAX_HIGH_A}"
            )

        if home_angle >= self.MAX_LOW_A and low_angle <= self.MAX_HIGH_A:
            self.home_angle = home_angle
        else:
            raise ValueError(
                f"home_angle needs to be between {self.MAX_LOW_A} and {self.MAX_HIGH_A}"
            )

        self.description = description
        self.designation = designation

    @property
    def position_us(self) -> int:
        return self.servo_ctl.get_position_us(self.channel)

    @position_us.setter
    def position_us(self, value: int):
        self.servo_ctl.set_target_us(self.channel, value)

    def stop(self) -> None:
        self.servo_ctl.stop_channel(self.channel)
