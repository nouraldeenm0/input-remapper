#!/usr/bin/python3
# -*- coding: utf-8 -*-
# key-mapper - GUI for device specific keyboard mappings
# Copyright (C) 2020 sezanzeb <proxima@hip70890b.de>
#
# This file is part of key-mapper.
#
# key-mapper is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# key-mapper is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with key-mapper.  If not, see <https://www.gnu.org/licenses/>.


"""Device and evdev stuff that is independent from the display server."""


import subprocess
import multiprocessing

import evdev

from keymapper.logger import logger


def can_grab(path):
    """Can input events from the device be read?

    Parameters
    ----------
    path : string
        Path in dev, for example '/dev/input/event7'
    """
    p = subprocess.run(['fuser', '-v', path])
    return p.returncode == 1


class KeycodeReader:
    """Keeps reading keycodes in the background for the UI to use.

    When a button was pressed, the newest keycode can be obtained from this
    object. This was written before I figured out there is get_keycode in Gdk.
    """
    def __init__(self):
        self.virtual_devices = []

    def clear(self):
        """Next time when reading don't return the previous keycode."""
        # read all of them to clear the buffer or whatever
        for virtual_device in self.virtual_devices:
            while virtual_device.read_one():
                pass

    def start_reading(self, device):
        """Tell the evdev lib to start looking for keycodes.

        If read is called without prior start_reading, no keycodes
        will be available.
        """
        paths = _devices[device]['paths']

        logger.debug(
            'Starting reading keycodes for %s on %s',
            device,
            ', '.join(paths)
        )

        # Watch over each one of the potentially multiple devices per hardware
        self.virtual_devices = [
            evdev.InputDevice(path)
            for path in paths
        ]

    def read(self):
        """Get the newest key or None if none was pressed."""
        newest_keycode = None
        for virtual_device in self.virtual_devices:
            while True:
                event = virtual_device.read_one()
                if event is None:
                    break
                if event.type == evdev.ecodes.EV_KEY and event.value == 1:
                    # value: 1 for down, 0 for up, 2 for hold.
                    # this happens to report key codes that are 8 lower
                    # than the ones reported by xev
                    newest_keycode = event.code + 8
        return newest_keycode


# not used anymore since the overlooked get_keycode function is now being used
# keycode_reader = KeycodeReader()


def _get_devices(pipe):
    """Group devices and get relevant infos per group.

    Returns a list containing mappings of
    {group_name: {paths: [paths], devices: [names]} for input devices.

    For example, group_name could be "Logitech USB Keyboard", devices might
    contain "Logitech USB Keyboard System Control" and "Logitech USB Keyboard".
    paths is a list of files in /dev/input that belong to the devices.

    They are grouped by usb port.
    """
    """
    evdev.list_devices -> string[] dev/input/event# paths
    device = evdev.InputDevice(path)
    device.capabilities().keys() ein array mit evdev.ecodes.EV_KEY oder
    irgendn stuff der nicht interessiert
    
    device.phys -> 
    
    device.phys usb-0000:03:00.0-4/input2
    device.phys usb-0000:03:00.0-4/input1
    device.phys usb-0000:03:00.0-4/input0
    device.phys usb-0000:03:00.0-3/input1
    device.phys usb-0000:03:00.0-3/input1
    device.phys usb-0000:03:00.0-3/input0
    """

    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]

    # group them together by usb device because there could be stuff like
    # "Logitech USB Keyboard" and "Logitech USB Keyboard Consumer Control"
    grouped = {}
    for device in devices:
        # only keyboard devices
        # https://www.kernel.org/doc/html/latest/input/event-codes.html
        if evdev.ecodes.EV_KEY not in device.capabilities().keys():
            continue

        usb = device.phys.split('/')[0]
        if grouped.get(usb) is None:
            grouped[usb] = []
        grouped[usb].append((device.name, device.path))

    # now write down all the paths of that group
    result = {}
    for group in grouped.values():
        names = [entry[0] for entry in group]
        devs = [entry[1] for entry in group]
        shortest_name = sorted(names, key=len)[0]
        result[shortest_name] = {
            'paths': devs,
            'devices': names
        }

    pipe.send(result)


# populate once for the whole app. Since InputDevice destructors take
# quite some time, do this in a process that can take as much time as it
# wants after piping the result.
pipe = multiprocessing.Pipe()
multiprocessing.Process(target=_get_devices, args=(pipe[1],)).start()
# block until devices are available
_devices = pipe[0].recv()
logger.info('Found %s', ', '.join([f'"{name}"' for name in _devices]))


def get_devices():
    return _devices
