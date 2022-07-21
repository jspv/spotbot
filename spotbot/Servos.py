import re
from typing import Any


class Servo(object):
    MAX_HIGH_US = 3000
    MIN_LOW_US = 300
    MAX_HIGH_DEG = 270
    MIN_LOW_DEG = 0
    MAX_CHANNELS = 18

    # Servo controller to be provided externally via this class attribute.
    servo_ctl = None

    def __init__(
        self,
        lettermap: str,
        channel: int,
        description: str,
        designation: str = "",
        max_us: int = 3000,
        min_us: int = 300,
        max_deg: float = 180.0,
        min_deg: float = 0.0,
        home_deg: float = 90.0,
        angle1_us: int = 1500,
        angle1_deg: float = 90.0,
        angle2_us: int = 1000,
        angle2_deg: float = 0.0,
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

        if min_us >= self.MIN_LOW_US and min_us <= self.MAX_HIGH_US:
            self.min_us = min_us
        else:
            raise ValueError(
                f"min_us needs to be between {self.MIN_LOW_US} and {self.MAX_HIGH_US}"
            )

        if max_us >= self.MIN_LOW_US and max_us <= self.MAX_HIGH_US:
            self.max_us = max_us
        else:
            raise ValueError(
                f"max_us needs to be between {self.MIN_LOW_US} and {self.MAX_HIGH_US}"
            )

        if angle1_us >= self.MIN_LOW_US and angle1_us <= self.MAX_HIGH_US:
            self.angle1_us = angle1_us
        else:
            raise ValueError(
                f"angle1_us needs to be between {self.MIN_LOW_US} and {self.MAX_HIGH_US}"
            )

        if angle2_us >= self.MIN_LOW_US and angle2_us <= self.MAX_HIGH_US:
            self.angle2_us = angle2_us
        else:
            raise ValueError(
                f"angle2_us needs to be between {self.MIN_LOW_US} and {self.MAX_HIGH_US}"
            )

        if min_deg >= self.MIN_LOW_DEG and min_deg <= self.MAX_HIGH_DEG:
            self.min_deg = min_deg
        else:
            raise ValueError(
                f"min_deg needs to be between {self.MIN_LOW_DEG} and {self.MAX_HIGH_DEG}"
            )

        if max_deg >= self.MIN_LOW_DEG and max_deg <= self.MAX_HIGH_DEG:
            self.max_deg = max_deg
        else:
            raise ValueError(
                f"max_deg needs to be between {self.MIN_LOW_DEG} and {self.MAX_HIGH_DEG}"
            )

        if home_deg >= self.MIN_LOW_DEG and home_deg <= self.MAX_HIGH_DEG:
            self.home_deg = home_deg
        else:
            raise ValueError(
                f"home_deg needs to be between {self.MIN_LOW_DEG} and {self.MAX_HIGH_DEG}"
            )

        if angle1_deg >= self.MIN_LOW_DEG and angle1_deg <= self.MAX_HIGH_DEG:
            self.angle1_deg = angle1_deg
        else:
            raise ValueError(
                f"angle1_deg needs to be between {self.MIN_LOW_DEG} and {self.MAX_HIGH_DEG}"
            )

        if angle2_deg >= self.MIN_LOW_DEG and angle2_deg <= self.MAX_HIGH_DEG:
            self.angle2_deg = angle2_deg
        else:
            raise ValueError(
                f"angle2_deg needs to be between {self.MIN_LOW_DEG} and {self.MAX_HIGH_DEG}"
            )

        self.description = description
        self.designation = designation

    @property
    def position_us(self) -> int:
        return self.servo_ctl.get_position_us(self.channel)

    @position_us.setter
    def position_us(self, value: int):
        self.servo_ctl.set_target_us(self.channel, value)

    @property
    def position_angle(self) -> float:
        # todo
        return 123.4

    @position_angle.setter
    def position_angle(self, value: float):
        # todo
        pass

    def stop(self) -> None:
        self.servo_ctl.stop_channel(self.channel)
