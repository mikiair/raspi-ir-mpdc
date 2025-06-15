=============
raspi-ir-mpdc
=============
This is a configurable Python service to run on `Raspberry Pi <https://www.raspberrypi.org>`_.

**raspi-ir-mpdc** runs a Python script as a service on Raspberry Pi.

Key events from IR remote control can be configured to control a MPD/Mopidy server. For that purpose, `python-mpd2 <https://pypi.org/project/python-mpd2/>`_ package is used as a MPD client interface.

Required packages
-----------------
* `Mopidy <https://mopidy.com/>`_ with `Mopidy-MPD <https://mopidy.com/ext/mpd>`_ extension (or some other MPD server)
* `python3-systemd <https://github.com/systemd/python-systemd>`_
* python3-mpd / `python-mpd2 <https://github.com/Mic92/python-mpd2>`_
* `ir-keytable` to process IR remote data and map to key events
* `python-evdev <https://pypi.org/project/evdev/>`_

Installation
------------
Download raspi-ir-mpdc via **Code** button or from `Releases <https://github.com/mikiair/raspi-ir-mpdc/releases>`_ page (you most likely did already).
Unzip the received file:

   ``unzip raspi-ir-mpdc-main.zip -d ~/raspi-ir-mpdc``

Configure the service by editing the file ``raspi-ir-mpdc.conf`` according to your external hardware circuit set-up (see Configuration_).
Then simply run the script ``install`` in the **script** sub-folder. It will download and install the required packages, 
copy the files to their destinations, will register the service, and finally start it.

If you need to change the configuration after installation, you might use the script ``reconfigure`` after editing the source configuration file.
This will stop the service, copy the changed configuration file to **/etc** folder (overwrites previous version!), and then start the service again.

If you downloaded a newer version of the service the script ``update`` will handle stop and start of the service, and will copy the new Python and service files.
However, this will not update any underlying packages or services.

For uninstall, use the provided script ``uninstall``.

Configuration
-------------
The configuration is defined in the file ``raspi-ir-mpdc.conf``. Before installation, you will find the source file in the folder where you unzipped the package files. 
After installation, the active version is in **/etc** folder.

Section [IR]
============
Section ``[IR]`` is mandatory. It requires the definition of an input device to read key events from, and a list of key events linked to triggered MPD actions.

1) The ``InputDevice`` key-value-pair must be set as follows:

   ``InputDevice = device_path``
   
   ``device_path``
     Must be a path starting with ``/dev/input/event`` or an integer number (0, 1, 2...).
     It selects the input device, like an IR remote, which sends key commands to be processed and mapped to MPD events.

   e.g.

   ``InputDevice = /dev/input/event0``

   configures the first available input device to be used as a source for the service.

#) The list of ``KEY_...xxx`` key-value-pairs must be created based on this pattern:

   ``KEY_xxx = trigger_event[, keystate]``

   ``KEY_xxx``
     Any of the predefined Linux key event codes (list with ``cat /usr/include/linux/input-event-codes.h | grep '#define KEY_'``).
     They must be linked to incoming IR remote data in your own custom keytable file.
   ``trigger_event``
     The MPD event to trigger. One of:
   
     * play_pause - toggle playback state between *play* and *pause*
     * play_stop - toggle playback state between *play* and *stop*
     * prev_track - go to the previous track/stream in the playlist
     * next_track - go to the next track/stream in the playlist
     * mute - toggle output state between *mute* and *unmute*
     * vol_up - increase output volume
     * vol_dn - decrease output volume
     * prev_src - switch to the previous source
     * next_src - switch to the next source
     * repeat - enable/disable track/playlist repeat
     * single - enable/disable stop after track
     * random - enable/disable random track
     * consume - enable/disable track removed after play
     * fastfwd - advance the playing track position by 10 seconds
     * rewind - rewind the playing track position by 10 seconds

   ``keystate``
     (*optional*) The key state to act on. One of:

     * up - default, event(s) will be triggered when key is released
     * down    - ...when key is pressed
     * hold    - ...while key is held
     * dn_hold - ...when key is pressed down and while held
     
   e.g.
   
   ``KEY_VOLUMEUP = vol_up, dn_hold``
   
   configures the KEY_VOLUMEUP event to trigger the *vol_up* event of the MPD server when the key on the IR remote is pressed down and repeatedly while it is held.

Section [MPD]
=============
This is an optional section.

1) Optionally specify the MPD server to connect to. Default is ``localhost``.

   ``mpdhost = servername``
   
   ``servername``
     Name of the MPD server to connect to or its local IP address.
     
#) Optionally specify the port the MPD server uses. Default is 6600.

   ``mpdport = portnumber``
   
   ``portnumber``
     The port number which is used by the MPD server for connection.
   
#) Optionally specify a timeout in seconds to wait for connection built up. Default is 60 seconds.

   ``timeout = timeout_in_seconds``
   
   ``timeout_in_seconds``
     Time to wait for establishing the connection to the MPD server in seconds.
