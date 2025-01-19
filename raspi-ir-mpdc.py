#!/usr/bin/env python

__author__ = "Michael Heise"
__copyright__ = "Copyright (C) 2025 by Michael Heise"
__license__ = "Apache License Version 2.0"
__version__ = "1.0.0"
__date__ = "01/19/2025"

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
import asyncio
import logging
import signal
import sys

# local imports
import RaspiBaseMPDClient

# 3rd party imports
from evdev import InputDevice

# import configparser
# import time
# import weakref
# from systemd.journal import JournalHandler


class RaspiIRMPDClient(RaspiBaseMPDClient):
    CONFIGFILE = "/etc/raspi-ir-mpdc.conf"
    INPUTDEVICE_PATH = "/dev/input/event"

    def __init__(self):
        self._inputDevice = None
        self._keyevents = {}

        self.isValidIR = False

    def checkConfig(self):
        """Return True if the configuration has mandatory section IR."""
        return self.config.has_section("IR")

    def configKeyEvent(self, key, triggered_event):
        """Configure one key event to be handled."""

        if not self.checkKeyEvent(key):
            return False

        if not self.checkTriggeredEvent(triggered_event):
            return False

        return self.setupKeyEvent(key, triggered_event)

    def checkKeyEvent(self, key):
        """Return True if key is not in _keyevents dictionary (= not yet defined)."""
        if key in self._keyevents:
            self._log.error(f"Key event {key} already defined!")
            return False
        return True

    def setupKeyEvent(self, key, triggered_event):
        """Setup dictionary entry for key event."""
        try:
            event_func = getattr(self, triggered_event)

            if not event_func:
                raise ValueError("Could not determine event function!")

            self._keyevents[key] = event_func
            return True
        except Exception as e:
            self._log.error(f"Error while setting up key event! ({e})")
            return False

    def initIR(self):
        """Evaluate the data read from config file to set the IR device and events"""
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
                self._log.info(f"Key/button configuration '{key} = {value}'")
                if not self.configKeyEvent(upperKey, value.lower()):
                    return False
                continue

            self._log.info(f"Invalid key '{key}'!")
            return False

        self.isValidIR = True
        return True

    async def keyhandlerLoop(self):
        async for ev in self._inputDevice.async_read_loop():
            print(repr(ev))


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
        asyncio.run(mpdclient.keyhandlerLoop())

        # while True:
        #    time.sleep(0.1)

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
