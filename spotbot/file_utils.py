import yaml
from schema import Schema, SchemaError, Or, And, Regex, Optional
import serial
import sys


def load_configuration_file(
    configfile,
    defaults={
        "tty": "/dev/ttyS0",
        "baudrate": 9600,
        "parity": serial.PARITY_NONE,
        "stopbits": serial.STOPBITS_ONE,
        "bytesize": serial.EIGHTBITS,
        "timeout": None,
    },
):

    if configfile is None:
        return defaults

    with open(configfile) as fd:
        config = yaml.safe_load(fd)

    config_schema = Schema(
        {
            "servoboard": str,
            "serial_settings": {
                Optional("tty", default=defaults["tty"]): str,
                Optional("baudrate", default=defaults["baudrate"]): Or(
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
                Optional("parity", default=defaults["parity"]): Or("N", "E", "O"),
                Optional("stopbits", default=defaults["stopbits"]): Or(1, 2),
                Optional("bytesize", default=defaults["bytesize"]): Or(7, 8),
                Optional("timeout", default=defaults["timeout"]): Or(float, None),
            },
        }
    )
    try:
        config = config_schema.validate(config)
    except SchemaError as se:
        sys.exit(f"{configfile}: {se.code}")

    return config


def load_servo_configuration_file(configfile):
    config_schema = Schema(
        [
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
        ]
    )

    with open(configfile) as fd:
        config = yaml.safe_load(fd)

    try:
        config_schema.validate(config)
    except SchemaError as se:
        sys.exit(f"{configfile}: {se.code}")

    return config
