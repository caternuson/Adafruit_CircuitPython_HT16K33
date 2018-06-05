# The MIT License (MIT)
#
# Copyright (c) 2018 Carter Nelson, modified from:
# Copyright (c) 2016 Radomir Dopieralski & Tony DiCola for Adafruit Industries
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
`adafruit_ht16k33.ht16k33`
===========================

* Authors: Carter Nelson modified from original version by
           Radomir Dopieralski & Tony DiCola for Adafruit Industries

"""

from adafruit_bus_device import i2c_device
from micropython import const


_HT16K33_BLINK_CMD = const(0x80)
_HT16K33_BLINK_DISPLAYON = const(0x01)
_HT16K33_CMD_BRIGHTNESS = const(0xE0)
_HT16K33_OSCILATOR_ON = const(0x21)


class HT16K33:
    """The base class for all displays. Contains common methods.

    The HT16K33 uses memory mapping to control LEDs arranged in 16 segments
    with 8 commons. The layout for the 16 x 8 byte memory is shown below. The
    device has no notion of xy coordinates, but the one shown is what is used
    for this class.

               R = ROW  C = COL  memory address shown in []
    --x
    |       R0 R1 R2 R3 R4 R5 R6 R7 : R8 R9 R10 R11 R12 R13 R14 R15
    y   C0          [0x00]          :           [0x01]
        C1          [0x02]          :           [0x03]
        C2          [0x04]          :           [0x05]
        C3          [0x06]          :           [0x07]
        C4          [0x08]          :           [0x09]
        C5          [0x0A]          :           [0x0B]
        C6          [0x0C]          :           [0x0D]
        C7          [0x0E]          :           [0x0F]

    The 8 bits at each address control the rows as shown below.

                       D7 D6 D5 D4 D3 D2 D1 D0
                        7  6  5  4  3  2  1  0
                       15 14 13 12 11 10  9  8

    For example, to turn on the LED at (x, y) = (11, 5), set the D3 bit of 0x0B.

    """
    def __init__(self, i2c, address=0x70, size=(16,8), auto_write=True):
        self.i2c_device = i2c_device.I2CDevice(i2c, address)
        self._temp = bytearray(1)
        self._buffer = bytearray(17)
        self._size = size
        self._auto_write = auto_write
        self.fill(0)
        self._write_cmd(_HT16K33_OSCILATOR_ON)
        self._blink_rate = None
        self._brightness = None
        self.blink_rate = 0
        self.brightness = 15

    @property
    def auto_write(self):
        return self._auto_write

    @auto_write.setter
    def auto_write(self, auto_write):
        self._auto_write = auto_write

    @property
    def size(self):
        return self._size

    @property
    def blink_rate(self):
        return self._blink_rate

    @blink_rate.setter
    def blink_rate(self, rate):
        """The blink rate. Range 0-3."""
        if not 0 <= rate <= 3:
            raise ValueError('Blink rate must be an integer in the range: 0-3')
        rate = rate & 0x03
        self._blink_rate = rate
        self._write_cmd(_HT16K33_BLINK_CMD |
                        _HT16K33_BLINK_DISPLAYON | rate << 1)

    @property
    def brightness(self):
        return self._brightness

    @brightness.setter
    def brightness(self, brightness):
        """The brightness. Range 0-15."""
        if not 0 <= brightness <= 15:
            raise ValueError('Brightness must be an integer in the range: 0-15')
        brightness = brightness & 0x0F
        self._brightness = brightness
        self._write_cmd(_HT16K33_CMD_BRIGHTNESS | brightness)

    def __getitem__(self, key):
        x, y = key
        return self._pixel(x, y)

    def __setitem__(self, key, value):
        x, y = key
        self._pixel(x, y, value)

    def show(self):
        """Refresh the display and show the changes."""
        with self.i2c_device:
            # Byte 0 is 0x00, address of LED data register. The remaining 16
            # bytes are the display register data to set.
            self.i2c_device.write(self._buffer)

    def fill(self, color):
        """Fill the whole display with the given color."""
        fill = 0xff if color else 0x00
        for i in range(16):
            self._buffer[i+1] = fill
        if self._auto_write:
            self.show()

    def _pixel(self, x, y, color=None):
        if not 0 <= x < self.size[0]:
            raise ValueError('X value out of range: 0-{}'.format(self.size[0]-1))
        if not 0 <= y < self.size[1]:
            raise ValueError('Y value out of range: 0-{}'.format(self.size[1]-1))
        addr = 2*y + x // 8
        mask = 1 << x % 8
        if color is None:
            return bool(self._buffer[addr + 1] & mask)
        if color:
            # set the bit
            self._buffer[addr + 1] |= mask
        else:
            # clear the bit
            self._buffer[addr + 1] &= ~mask
        if self._auto_write:
            self.show()

    def _write_cmd(self, byte):
        self._temp[0] = byte
        with self.i2c_device:
            self.i2c_device.write(self._temp)

    def _set_buffer(self, i, value):
        self._buffer[i+1] = value  # Offset by 1 to move past register address.

    def _get_buffer(self, i):
        return self._buffer[i+1]   # Offset by 1 to move past register address.
