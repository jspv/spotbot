"""
Maestro Servo Controller

Support for the Pololu Maestro line of servo controllers:
https://www.pololu.com/docs/0J40

Originally cloned from: https://github.com/FRC4564/Maestro/
re-cloned from: https://github.com/austin-bowen/pololu-maestro/
Edited by Justin Peavey - June 2022 to support UART

These functions provide access to many of the Maestro's capabilities using the Pololu serial protocol.
"""

from functools import wraps
from sysconfig import get_python_version
from typing import Mapping, MutableSequence, Union

import serial  # expecting pyserial
import sys


def _micro_maestro_not_supported(method):
    """
    Methods using this decorator will raise a MicroMaestroNotSupportedError if
    the Controller is for the Micro Maestro.
    """

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        __doc__ = method.__doc__
        if self.is_micro:
            raise MicroMaestroNotSupportedError(
                'The method "{}" is not supported by the Micro Maestro.'.format(
                    method.__name__
                )
            )

        return method(self, *args, **kwargs)

    return wrapper


def _get_lsb_msb(value: int):
    assert (
        0 <= value <= 16383
    ), "value was {}; must be in the range of [0, 2^14 - 1].".format(value)
    lsb = value & 0x7F  # 7 bits for least significant byte
    msb = (value >> 7) & 0x7F  # shift 7 and take next 7 bits for msb
    return lsb, msb


class ServoController:
    """
    When connected via USB, the Maestro creates two virtual serial ports
    /dev/ttyACM0 for commands and /dev/ttyACM1 for communications.
    Be sure the Maestro is configured for "USB Dual Port" serial mode.
    "USB Chained Mode" may work as well, but hasn't been tested.

    Pololu protocol allows for multiple Maestros to be connected to a single
    serial port. Each connected device is then indexed by number.
    This device number defaults to 0x0C (or 12 in decimal), which this module
    assumes.  If two or more controllers are connected to different serial
    ports, or you are using a Windows OS, you can provide the tty port.  For
    example, '/dev/ttyACM2' or for Windows, something like 'COM3'.

    TODO: Automatic serial reconnect.
    """

    class SerialCommands:
        # Headers
        POLOLU_PROTOCOL = 0xAA
        DEFAULT_DEVICE_NUMBER = 0x0C

        # Commands
        SET_TARGET = 0x04
        SET_SPEED = 0x07
        SET_ACCELERATION = 0x09
        GET_POSITION = 0x10
        GET_ERRORS = 0x21
        GO_HOME = 0x22
        STOP_SCRIPT = 0x24
        RESTART_SCRIPT_AT_SUBROUTINE = 0x27
        RESTART_SCRIPT_AT_SUBROUTINE_WITH_PARAMETER = 0x28
        GET_SCRIPT_STATUS = 0x2E
        # - Not available on the Micro
        SET_PWM = 0x0A
        GET_MOVING_STATE = 0x13
        SET_MULTIPLE_TARGETS = 0x1F

    class Errors:
        """
        See the documentation for descriptions of these errors:
        https://www.pololu.com/docs/0J40/4.e
        """

        SERIAL_SIGNAL_ERROR = 1 << 0
        SERIAL_OVERRUN_ERROR = 1 << 1
        SERIAL_BUFFER_FULL_ERROR = 1 << 2
        SERIAL_CRC_ERROR = 1 << 3
        SERIAL_PROTOCOL_ERROR = 1 << 4
        SERIAL_TIMEOUT_ERROR = 1 << 5
        SCRIPT_STACK_ERROR = 1 << 6
        SCRIPT_CALL_STACK_ERROR = 1 << 7
        SCRIPT_PROGRAM_COUNTER_ERROR = 1 << 8

    def __init__(
        self,
        is_micro=False,
        tty: str = "/dev/ttyACM0",
        baudrate=9600,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        device: int = SerialCommands.DEFAULT_DEVICE_NUMBER,
        safe_close: bool = True,
        timeout: float = None,
    ):
        """
        :param is_micro: Whether or not the device is the Micro Maestro, which lacks some functionality.
        :param tty:
        :param device:
        :param safe_close: If `True`, tells the Maestro to stop sending servo signals before closing the connection.
        :param timeout: Read timeout in seconds.
        """

        self.is_micro = is_micro

        # Open the command port
        self._port = serial.Serial(
            tty,
            baudrate=baudrate,
            parity=parity,
            stopbits=stopbits,
            bytesize=bytesize,
            timeout=timeout,
        )
        # self._port = serial.Serial(tty, timeout=timeout)

        # Command lead-in and device number are sent for each Pololu serial command.
        self._pololu_cmd = bytes((self.SerialCommands.POLOLU_PROTOCOL, device))

        self.safe_close = safe_close

        # Track target position for each servo
        self.targets_us: MutableSequence[Union[int, float]] = [0] * 24

        # Servo minimum and maximum targets can be restricted to protect components
        self.min_targets_us: MutableSequence[Union[None, int, float]] = [None] * 24
        self.max_targets_us: MutableSequence[Union[None, int, float]] = [None] * 24

        self._closed = False

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _read(self, byte_count: int) -> bytes:
        """
        :raises TimeoutError: Connection timed out waiting to read the specified number of bytes.
        """
        assert byte_count > 0
        data = self._port.read(byte_count)
        if len(data) != byte_count:
            raise TimeoutError(
                "Tried to read {} bytes, but only got {}.".format(byte_count, len(data))
            )
        return data

    def close(self):
        """Cleanup by closing USB serial port."""
        if self._closed:
            return

        if self.safe_close:
            for channel in range(24):
                self.stop_channel(channel)

        self._port.close()

        self._closed = True

    def get_errors(self):
        """
        Use this command to examine the errors that the Maestro has detected. Section 4.e lists the specific errors that
        can be detected by the Maestro. The error register is sent as a two-byte response immediately after the command
        is received, then all the error bits are cleared. For most applications using serial control, it is a good idea
        to check errors continuously and take appropriate action if errors occur.

        See the Errors class for error values that can be and-ed with the result of this method to determine exactly
        which errors have occurred.

        :return: 0 if no errors have occurred since the last check; non-zero if an error has occurred.
        :raises TimeoutError: Connection timed out.
        """
        self.send_cmd(bytes((self.SerialCommands.GET_ERRORS,)))
        data = self._read(2)
        return data[0] << 8 | data[1]

    def go_home(self):
        """
        Sends all servos and outputs to their home positions, just as if an
        error had occurred. For servos and outputs set to "Ignore", the
        position will be unchanged.
        """
        self.send_cmd(bytes((self.SerialCommands.GO_HOME,)))

    def script_is_running(self):
        """
        :return: True if a script is running; False otherwise.
        :raises TimeoutError: Connection timed out.
        """
        self.send_cmd(bytes((self.SerialCommands.GET_SCRIPT_STATUS,)))

        # Maestro returns 0x00 if a script is running
        return self._read(1)[0] == 0

    def send_cmd(self, cmd: Union[bytes, bytearray]):
        """Send a Pololu command out the serial port."""
        self._port.write(self._pololu_cmd + cmd)
        self._port.flush()

    @_micro_maestro_not_supported
    def set_pwm(self, on_time_us: Union[int, float], period_us: Union[int, float]):
        """
        Sets the PWM output to the specified on time and period.
        This command is not available on the Micro Maestro.

        :param on_time_us: PWM on-time in microseconds.
        :param period_us: PWM period in microseconds.
        """
        on_time = int(round(48 * on_time_us))  # The command uses 1/48th us intervals
        on_time_lsb, on_time_msb = _get_lsb_msb(on_time)
        period = int(round(48 * period_us))  # The command uses 1/48th us intervals
        period_lsb, period_msb = _get_lsb_msb(period)
        self.send_cmd(
            bytes(
                (
                    self.SerialCommands.SET_PWM,
                    on_time_lsb,
                    on_time_msb,
                    period_lsb,
                    period_msb,
                )
            )
        )

    def set_range(
        self, channel: int, min_us: Union[int, float], max_us: Union[int, float]
    ):
        """
        Set channels min and max value range.  Use this as a safety to protect from accidentally moving outside known
        safe parameters. A setting of 0 or None allows unrestricted movement.

        Note that the Maestro itself is configured to limit the range of servo travel which has precedence over these
        values. Use the Maestro Control Center to configure ranges that are saved to the controller. Use setRange for
        software controllable ranges.
        """
        self.min_targets_us[channel] = min_us
        self.max_targets_us[channel] = max_us

    def stop_channel(self, channel: int):
        """
        Sets the target of the specified channel to 0, causing the Maestro to stop sending PWM signals on that channel.

        :param channel: PWM channel to stop sending PWM signals to.
        """
        self.set_target(channel, 0)

    def stop_script(self):
        """Causes the script to stop, if it is currently running."""
        self.send_cmd(bytes((self.SerialCommands.STOP_SCRIPT,)))

    def get_min(self, channel: int):
        """Return minimum channel range value."""
        return self.min_targets_us[channel]

    def get_max(self, channel: int):
        """Return maximum channel range value."""
        return self.max_targets_us[channel]

    def set_target(self, channel: int, target: int):
        """
        Set channel to a specified target value.  Servo will begin moving based
        on Speed and Acceleration parameters previously set.
        Target values will be constrained within Min and Max range, if set.
        The Pololu protocol works in pulse-widths of quarter-microseconds
        For servos, target represents the pulse width in of quarter-microseconds
        Servo center is at 1500 microseconds, or 6000 quarter-microseconds
        Typically valid servo range is 3000 to 9000 quarter-microseconds
        If channel is configured for digital output, values < 6000 = Low output
        """

        target_us = target / 4

        # If min is defined and target is below, force to min
        min_target_us = self.min_targets_us[channel]
        if min_target_us and target_us < min_target_us:
            target_us = min_target_us

        # If max is defined and target is above, force to max
        max_target_us = self.max_targets_us[channel]
        if max_target_us and target_us > max_target_us:
            target_us = max_target_us

        # Record target value
        self.targets_us[channel] = target_us

        # Send the target to the Maestro
        lsb, msb = _get_lsb_msb(target)
        self.send_cmd(bytes((self.SerialCommands.SET_TARGET, channel, lsb, msb)))

    def set_target_us(self, channel: int, target_us: float):
        """set the target of the serveo using microseconds"""
        target = int(round(4 * target_us))
        return self.set_target(channel, target)

    def set_targets_us(self, targets_us: Mapping[int, Union[int, float]]):
        """
        Set multiple channel targets at once.

        The Micro Maestro does not support the "set multiple targets" command, so this method will simply set each
        channel target one at a time.

        The other Maestro models, however, support the option of setting the targets for a block of channels using a
        single command.  This method will use that "set multiple targets" command when possible, for maximum efficiency.

        :param targets: A dict mapping channels to their targets (in microseconds).
        """
        if self.is_micro:
            for channel, target_us in targets_us.items():
                self.set_target_us(channel, target_us)

        # Non-Micro Maestros support sending blocks of target values with one command
        else:
            # Use targets to build a structure of target blocks
            channels = sorted(targets_us.keys())
            prev_channel = first_channel = channels[0]
            target = targets_us[first_channel]
            # Structure: {channelM: [targetM, targetM+1, ..., targetN], ...}
            target_blocks = {first_channel: [target_us]}
            for channel in channels[1:]:
                target_us = targets_us[channel]

                if channel - 1 == prev_channel:
                    target_blocks[first_channel].append(target_us)
                else:
                    first_channel = channel
                    target_blocks[first_channel] = [target_us]

                prev_channel = channel

            for first_channel, target_block in target_blocks.items():
                target_count = len(target_block)

                # If there is only one target in the block, use the single "set target" command
                if target_count == 1:
                    self.set_target_us(first_channel, target_block[0])

                # If there is more than one target in the block, set them all at once with the
                # "set multiple targets" command.
                else:
                    cmd = bytearray(
                        (
                            self.SerialCommands.SET_MULTIPLE_TARGETS,
                            target_count,
                            first_channel,
                        )
                    )
                    for target_us in target_block:
                        target_us = int(float(4 * target_us))
                        cmd += bytes(_get_lsb_msb(target_us))
                    self.send_cmd(cmd)

    def set_speed(self, channel: int, speed: int):
        """
        Set speed of channel
        Speed is measured as 0.25microseconds/10milliseconds
        For the standard 1ms pulse width change to move a servo between extremes, a speed
        of 1 will take 1 minute, and a speed of 60 would take 1 second. Speed of 0 is unrestricted.
        """
        lsb, msb = _get_lsb_msb(speed)
        self.send_cmd(bytes((self.SerialCommands.SET_SPEED, channel, lsb, msb)))

    def set_acceleration(self, channel: int, acceleration: int):
        """
        Set acceleration of channel
        This provide soft starts and finishes when servo moves to target position.
        Valid values are from 0 to 255. 0 = unrestricted, 1 is slowest start.
        A value of 1 will take the servo about 3s to move between 1ms to 2ms range.
        """
        lsb, msb = _get_lsb_msb(acceleration)
        self.send_cmd(bytes((self.SerialCommands.SET_ACCELERATION, channel, lsb, msb)))

    def get_position(self, chan: int):
        """
        Get the current position of the device on the specified channel
        The raw protocol result is returned in a measure of
        quarter-microseconds, which mirrors the Target parameter of set target.
        This is not reading the true servo position, but the last target position sent
        to the servo. If the Speed is set to below the top speed of the servo, then
        the position result will align well with the actual servo position, assuming
        it is not stalled or slowed.

        :raises TimeoutError: Connection timed out.
        """
        self.send_cmd(bytes((self.SerialCommands.GET_POSITION, chan)))
        lsb = ord(self._port.read())
        msb = ord(self._port.read())
        return (msb << 8) | lsb

    def get_position_us(self, chan: int):
        """Return the current position of the servo in microseconds"""
        return self.get_position(chan) / 4

    def is_moving(self, channel: int):
        """
        Test to see if a servo has reached the set target position.  This only provides
        useful results if the Speed parameter is set slower than the maximum speed of
        the servo.  Servo range must be defined first using setRange. See setRange comment.

        ***Note if target position goes outside of Maestro's allowable range for the
        channel, then the target can never be reached, so it will appear to always be
        moving to the target.
        """
        target_us = self.targets_us[channel]
        return target_us and abs(target_us - self.get_position_us(channel)) < 0.01

    @_micro_maestro_not_supported
    def servos_are_moving(self):
        """
        Determines whether the servo outputs have reached their targets or are still changing, and will return True as
        long as there is at least one servo that is limited by a speed or acceleration setting still moving. Using this
        command together with the set_target command, you can initiate several servo movements and wait for all the
        movements to finish before moving on to the next step of your program.

        :returns: True if the Maestro reports that servos are still moving; False otherwise.
        :raises TimeoutError: Connection timed out.
        """
        self.send_cmd(bytes((self.SerialCommands.GET_MOVING_STATE,)))
        return self._read(1)[0] == 1

    def run_script_subroutine(self, subroutine: int):
        """
        Starts the script running at a location specified by the subroutine number argument. The subroutines are
        numbered in the order they are defined in your script, starting with 0 for the first subroutine. The first
        subroutine is sent as 0x00 for this command, the second as 0x01, etc. To find the number for a particular
        subroutine, click the "View Compiled Code..." button and look at the list below. Subroutines used this way
        should not end with the RETURN command, since there is no place to return to — instead, they should contain
        infinite loops or end with a QUIT command.

        :param subroutine: The subroutine number to run.
        """
        self.send_cmd(
            bytes((self.SerialCommands.RESTART_SCRIPT_AT_SUBROUTINE, subroutine))
        )

    def run_script_subroutine_with_parameter(self, subroutine: int, parameter: int):
        """
        This method is just like the "run_script_subroutine" method, except it loads a parameter on to the stack before
        starting the subroutine. Since data bytes can only contain 7 bits of data, the parameter must be between
        0 and 16383.

        :param subroutine: The subroutine number to run.
        :param parameter: The integer parameter to pass to the subroutine (range: 0 to 16383).
        :return:
        """
        parameter_lsb, parameter_msb = _get_lsb_msb(parameter)
        self.send_cmd(
            bytes(
                (
                    self.SerialCommands.RESTART_SCRIPT_AT_SUBROUTINE_WITH_PARAMETER,
                    subroutine,
                    parameter_lsb,
                    parameter_msb,
                )
            )
        )


class MicroMaestroNotSupportedError(Exception):
    """Raised when calling a method that is not supported by the Micro Maestro."""

    pass
