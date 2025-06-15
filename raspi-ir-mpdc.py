#!/usr/bin/env python

__author__ = "Michael Heise"
__copyright__ = "Copyright (C) 2025 by Michael Heise"
__license__ = "Apache License Version 2.0"
__version__ = "1.0.0"
__date__ = "06/15/2025"

"""MPD/Mopidy client service which is controlled by IR remote key events on Raspberry Pi
"""

#    Copyright 2025 Michael Heise (mikiair)
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

# standard imports
import logging
import signal
import sys

# 3rd party imports
from evdev import InputDevice, categorize, ecodes

# local imports
from raspimpdc import RaspiBaseMPDClient


class RaspiIRMPDClient(RaspiBaseMPDClient):
    INPUTDEVICE_PATH = "/dev/input/event"

    VALUES_KEYSTATE = ["up", "down", "hold", "dn_hold"]

    def __init__(self):
        super().__init__()

        self._inputDevice = None
        self._keyevents = {}

        self.isValidIR = False

    def checkConfig(self):
        """Return True if the configuration has mandatory section IR."""
        return self.config.has_section("IR")

    def configKeyEvent(self, key, eventConfig):
        """Configure one key event to be handled."""

        if not self.checkKeyEvent(key):
            return False

        triggered_event = eventConfig[0]
        if not self.checkTriggeredEvent(triggered_event):
            return False

        if len(eventConfig) == 2:
            keystate = self.checkKeyState(eventConfig[1].lower())
            if keystate == -1:
                return False
        else:
            # use 'up' as default
            keystate = 0

        return self.setupKeyEvent(key, triggered_event, keystate)

    def checkKeyEvent(self, key):
        """Return True if key represents a valid code and is not yet used."""
        if key not in ecodes.ecodes.keys():
            self._log.error(f"Key event {key} is not valid!")
            return False

        if ecodes.ecodes[key] in self._keyevents.keys():
            self._log.error(f"Key event {key} already defined!")
            return False

        return True

    def checkKeyState(self, statestr):
        """Return a keystate integer value or -1 if an invalid string is given."""
        if statestr not in self.VALUES_KEYSTATE:
            self._log.error(
                "Invalid event configuration! Only 'up', 'down', 'hold', or 'dn_hold' allowed!"
            )
            return -1
        return self.VALUES_KEYSTATE.index(statestr)

    def setupKeyEvent(self, key, triggered_event, keystate):
        """Setup dictionary entry for key event."""
        try:
            event_func = getattr(self, triggered_event)

            if not event_func:
                raise ValueError("Could not determine event function!")

            self._keyevents[ecodes.ecodes[key]] = (keystate, event_func)
            return True
        except Exception as e:
            self._log.error(f"Error while setting up key event! ({e})")
            return False

    def initIR(self):
        """Evaluate the data read from config file to set the IR device and events."""
        self._log.info("Init IR configuration.")
        configIR = self.config["IR"]

        self._vol_step = 1

        for key, value in configIR.items():
            upperKey = key.upper()

            if upperKey == "INPUTDEVICE":
                self._log.info(f"Input device configuration '{key} = {value}'")
                if self._inputDevice is not None:
                    self._log.error("Multiple input device definition is not allowed!")

                if value.lower().startswith(self.INPUTDEVICE_PATH):
                    self._inputDevice = InputDevice(value)
                    continue

                try:
                    deviceNum = int(value)
                    self._inputDevice = InputDevice(self.INPUTDEVICE_PATH + deviceNum)
                    continue
                except Exception:
                    self._log.error(
                        f"'{value}' does not identify an input device by number!"
                    )

                return False

            if upperKey.startswith("KEY_") or upperKey.startswith("BTN_"):
                self._log.info(f"Key/button configuration '{upperKey} = {value}'")
                if not self.configKeyEvent(upperKey, value.lower().split(",")):
                    return False
                continue

            self._log.info(f"Invalid key '{key}'!")
            return False

        self.isValidIR = True
        return True

    def keyhandlerLoop(self):
        """Read IR remote key events from the input device and trigger MPD actions.
        
        Acts only when key state is matching required condition (up, down, hold).
        """
        for event in self._inputDevice.read_loop():
            if event.type == ecodes.EV_KEY:
                keyEvent = categorize(event)
                self._log.debug(keyEvent)
                try:
                    if keyEvent.scancode in self._keyevents.keys():
                        keystate, triggered_event = self._keyevents[keyEvent.scancode]
                        if keyEvent.keystate == keystate or (
                            keyEvent.keystate & keystate != 0
                        ):
                            triggered_event()
                except Exception:
                    self._log.error(f"Could not handle '{keyEvent.keycode}'!")


def sigterm_handler(_signo, _stack_frame):
    """Clean exit on SIGTERM signal (when systemd stops the process)"""
    sys.exit(0)


def main():
    # install handler
    signal.signal(signal.SIGTERM, sigterm_handler)

    log = None
    mpdclient = None

    try:
        log = logging.getLogger(__name__)

        mpdclient = RaspiIRMPDClient()
        if log:
            mpdclient.initLogging(log)

        if not mpdclient.readConfigFile():
            sys.exit(-2)

        if not mpdclient.checkConfig():
            log.error("Invalid configuration file! (section [IR] missing)")
            sys.exit(-3)

        mpdclient.setLogLevel()

        if not mpdclient.initIR():
            log.error("Init IR failed!")
            sys.exit(-3)

        if not mpdclient.initMPD():
            log.error("Init MPD connection failed!")
            sys.exit(-4)

        if not mpdclient.isConnected and not mpdclient.connectMPD():
            log.error("Could not connect to MPD server - possibly timed out!")
            sys.exit(-5)

        log.info("Enter raspi-ir-mpdc service loop...")
        mpdclient.keyhandlerLoop()

    except Exception as e:
        if log:
            log.exception(f"Unhandled exception: {e}")
        sys.exit(-1)
    finally:
        if mpdclient and mpdclient.isConnected:
            if log:
                log.info("Disconnect from MPD.")
            mpdclient.mpd.disconnect()


# run as script only
if __name__ == "__main__":
    main()
