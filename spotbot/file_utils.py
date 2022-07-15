from ruamel.yaml import YAML
from schema import Schema, SchemaError, Or, And, Regex, Optional
from datetime import datetime
import serial
import sys


class ConfigFile(object):

    defaults = {
        "tty": "/dev/ttyS0",
        "baudrate": 9600,
        "parity": serial.PARITY_NONE,
        "stopbits": serial.STOPBITS_ONE,
        "bytesize": serial.EIGHTBITS,
        "timeout": None,
        "servo_config": "servo_config.yml",
        "pose_config": "pose_config.yml",
    }

    def __init__(self, configfile: str) -> None:
        self.configfile = configfile
        self.config = self.load()

    def load(self) -> dict:
        yaml = YAML()

        with open(self.configfile) as fd:
            config = yaml.load(fd)

        config_schema = Schema(
            {
                "servoboard": str,
                Optional("servo_config", default=self.defaults["servo_config"]): str,
                Optional("pose_config", default=self.defaults["pose_config"]): str,
                "serial_settings": {
                    Optional("tty", default=self.defaults["tty"]): str,
                    Optional("baudrate", default=self.defaults["baudrate"]): Or(
                        10,
                        300,
                        600,
                        1200,
                        2400,
                        4800,
                        9600,
                        14400,
                        19200,
                        38400,
                        57600,
                        115200,
                        128000,
                        256000,
                    ),
                    Optional("parity", default=self.defaults["parity"]): Or(
                        "N", "E", "O"
                    ),
                    Optional("stopbits", default=self.defaults["stopbits"]): Or(1, 2),
                    Optional("bytesize", default=self.defaults["bytesize"]): Or(7, 8),
                    Optional("timeout", default=self.defaults["timeout"]): Or(
                        float, None
                    ),
                },
                Optional("relay_settings"): {
                    "gpio": int,
                    "active_high": bool,
                },
            }
        )
        try:
            config = config_schema.validate(config)
        except SchemaError as se:
            sys.exit(f"{self.configfile}: {se.code}")

        return config


class ServoConfiFile(object):
    def __init__(self, configfile: str) -> None:
        self.configfile = configfile
        self.data = self.load()

    def load(self) -> dict:
        yaml = YAML()
        config_schema = Schema(
            {
                And(
                    str, Regex(r"^[A-R]$"), error="lettermap needs to be A through R"
                ): {
                    "position": And(
                        int,
                        lambda n: 0 <= n <= 17,
                        error="position needs to be between 0 and 17",
                    ),
                    "designation": And(
                        str,
                        lambda n: len(n) < 5,
                        error="designation too long <5 characters",
                    ),
                    "description": And(
                        str,
                        lambda n: len(n) < 30,
                        error="description too long, <30 characters",
                    ),
                    "high_us": And(int, lambda n: 300 <= n <= 3000),
                    "low_us": And(int, lambda n: 300 <= n <= 3000),
                    "high_pos": Or("high", "low"),
                    "high_angle": And(float, lambda n: 0 <= n <= 180),
                    "low_angle": And(float, lambda n: 0 <= n <= 180),
                    "home_angle": And(float, lambda n: 0 <= n <= 180),
                }
            }
        )

        with open(self.configfile) as fd:
            self.config = yaml.load(fd)

        try:
            config_schema.validate(self.config)
        except SchemaError as se:
            sys.exit(f"{self.configfile}: {se.code}")

        return self.config

    def save(self) -> None:
        yaml = YAML()
        now = datetime.now().replace(microsecond=0)

        self.config.yaml_set_start_comment(
            "This file automatically generated on {} by spotbot config".format(now)
        )

        with open(self.configfile, "w") as fd:
            yaml.dump(self.config, fd)
