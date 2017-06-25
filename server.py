#!/usr/bin/env python3

import time
import pymumble.pymumble_py3 as pymumble


def bot(host, nickname):
    # create the mumble instance
    mumble = pymumble.Mumble(host, user=nickname, port=64738)

    # identify this software
    mumble.set_application_string("dmr-bridge")

    # set default callbacks
    mumble.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_CONNECTED, callback_connected)

    # handle text messages
    mumble.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_TEXTMESSAGERECEIVED, callback_received_message)

    # handle incoming audio
    mumble.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_SOUNDRECEIVED, callback_received_sound)
    mumble.set_receive_sound(True)

    # start client
    mumble.start()
    mumble.is_ready()
    mumble.users.myself.unmute()

    time.sleep(30.0)


def callback_connected():
    print("Connected")


def callback_received_message(data):
    print("Message: %s" % data.message)


def callback_received_sound(user, chunk):
    pass


if __name__ == "__main__":
    bot("localhost", "Radio")
