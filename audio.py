""" Audio classes and functions including mumble bridge """

import pyaudio
import numpy as np
import pymumble.pymumble_py3 as pymumble
import hardware


class MumbleBridge:
    """ Bridge Mumble and connect audio device """

    def __init__(self, host, nickname):
        # radio hardware interface
        self.radio = hardware.Radio()

        # create the mumble instance
        self.mumble = pymumble.Mumble(host, user=nickname, port=64738, debug=False)

        # identify this software
        self.mumble.set_application_string("dmr-bridge")

        # set default callbacks
        self.mumble.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_CONNECTED, self.callback_connected)

        # handle text messages
        self.mumble.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_TEXTMESSAGERECEIVED, self.callback_received_message)

        # handle incoming audio
        self.mumble.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_SOUNDRECEIVED, self.callback_received_sound)
        self.mumble.set_receive_sound(True)

        # state for voice activation
        self.state = {
            'level': 0.0,
            'count': 0,
            'maxcount': 3,
            'activation_level': np.iinfo(np.uint16).max * 0.6
        }

        # radio state and buffer
        self.radio_buffer = b''
        self.radio_state = 0

        # open audio interface
        self.p = pyaudio.PyAudio()
        self.stream = None

    def connect(self):
        self.mumble.start()
        self.mumble.is_ready()

    def connected(self):
        return self.stream.is_active()

    def disconnect(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()

        self.p.terminate()

    def callback_connected(self):
        print("Connected")
        self.mumble.users.myself.unmute()

        self.stream = self.p.open(format=self.p.get_format_from_width(2),
                             channels=1,
                             rate=48000,
                             input=True,
                             output=True,
                             stream_callback=self.callback_audio,
                             frames_per_buffer=4096)

        self.stream.start_stream()

    def callback_received_message(self, data):
        print("Message: %s" % data.message)

    def callback_received_sound(self, user, chunk):
        # copy input to mumble input buffer
        self.radio_buffer = self.radio_buffer + chunk.pcm

    def callback_audio(self, in_data, frame_count, time_info, status):
        if self.voice_detection(in_data):
            # copy radio input to mumble output buffer
            self.mumble.sound_output.add_sound(in_data)

        # copy buffered mumble input buffer to radio output
        return self.get_radio_output(frame_count), pyaudio.paContinue

    def voice_detection(self, in_data):
        """ use approach in https://github.com/jeysonmc/python-google-speech-scripts/blob/master/stt_google.py
        for voice detection """
        # look for high input level
        input_frames = np.fromstring(in_data, dtype=np.uint16)

        # store current average level
        self.state['level'] = np.mean(input_frames)

        if self.state['level'] < (self.state['activation_level'] * 0.8) and self.state['count'] > 0:
            self.state['count'] = self.state['count'] - 1
        elif self.state['level'] > (self.state['activation_level'] * 1.2) and self.state['count'] < self.state['maxcount']:
            if self.state['count'] < 2:
                self.state['count'] = 2
            self.state['count'] = self.state['count'] + 1

        return self.state['count'] > 0

    def get_radio_output(self, frame_count):
        chunk_size = frame_count * 2

        if self.radio_state == 0 and len(self.radio_buffer) < chunk_size:
            # fill front with silence
            ret = (b'\0' * (chunk_size - len(self.radio_buffer))) + self.radio_buffer
            self.radio_state = 1
            self.radio_buffer = b''
        elif self.radio_state == 1 and len(self.radio_buffer) < chunk_size:
            # fill back with silence
            ret = self.radio_buffer + (b'\0' * (chunk_size - len(self.radio_buffer)))
            self.radio_state = 0
            self.radio_buffer = b''
        elif len(self.radio_buffer) > chunk_size:
            # chop some frames from the buffer
            ret = self.radio_buffer
            self.radio_buffer = self.radio_buffer[chunk_size:]
        else:
            # generate silence
            ret = np.zeros(frame_count, dtype=np.int16)

        return ret