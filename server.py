#!/usr/bin/env python3

import time
import pymumble.pymumble_py3 as pymumble
import pyaudio
import numpy as np
import hardware

# global mumble object
mumble = None

# global radio controller
radio = hardware.Radio()

# state for voice activation
state = {
    'level': 0.0,
    'count': 0,
    'maxcount': 3,
    'activation_level': np.iinfo(np.uint16).max * 0.6
}

# radio state and buffer
radio_buffer = b''
radio_state = 0


def bot(host, nickname):
    global mumble

    # create the mumble instance
    mumble = pymumble.Mumble(host, user=nickname, port=64738, debug=False)

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

    # open audio interface
    p = pyaudio.PyAudio()
    stream = p.open(format=p.get_format_from_width(2),
                    channels=1,
                    rate=48000,
                    input=True,
                    output=True,
                    stream_callback=callback_audio,
                    frames_per_buffer=4096)

    stream.start_stream()

    while stream.is_active():
        time.sleep(0.1)

    stream.stop_stream()
    stream.close()

    p.terminate()


def voice_detection(in_data):
    global state

    # look for high input level
    input_frames = np.fromstring(in_data, dtype=np.uint16)

    # store current average level
    state['level'] = np.mean(input_frames)

    if state['level'] < (state['activation_level'] * 0.8) and state['count'] > 0:
        state['count'] = state['count'] - 1
    elif state['level'] > (state['activation_level'] * 1.2) and state['count'] < state['maxcount']:
        if state['count'] < 2:
            state['count'] = 2
        state['count'] = state['count'] + 1

    return state['count'] > 0


def callback_connected():
    print("Connected")


def callback_received_message(data):
    print("Message: %s" % data.message)


def callback_received_sound(user, chunk):
    global radio_buffer, radio_state

    # copy input to mumble input buffer
    radio_buffer = radio_buffer + chunk.pcm


def get_radio_output(frame_count):
    global radio_buffer, radio_state
    chunk_size = frame_count * 2

    if radio_state == 0 and len(radio_buffer) < chunk_size:
        # fill front with silence
        ret = (b'\0' * (chunk_size - len(radio_buffer))) + radio_buffer
        radio_state = 1
        radio_buffer = b''
    elif radio_state == 1 and len(radio_buffer) < chunk_size:
        # fill back with silence
        ret = radio_buffer + (b'\0' * (chunk_size - len(radio_buffer)))
        radio_state = 0
        radio_buffer = b''
    elif len(radio_buffer) > chunk_size:
        # chop some frames from the buffer
        ret = radio_buffer
        radio_buffer = radio_buffer[chunk_size:]
    else:
        # generate silence
        ret = np.zeros(frame_count, dtype=np.int16)

    return ret


def callback_audio(in_data, frame_count, time_info, status):
    if voice_detection(in_data):
        # copy radio input to mumble output buffer
        mumble.sound_output.add_sound(in_data)

    # copy buffered mumble input buffer to radio output
    return get_radio_output(frame_count), pyaudio.paContinue


if __name__ == "__main__":
    bot("localhost", "Radio")
