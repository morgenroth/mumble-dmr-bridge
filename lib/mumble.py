import lib.hardware as hardware
from lib.audio import AudioBridge
import pymumble.pymumble_py3 as pymumble


class MumbleBridge:
    """ Bridge Mumble and connect audio device """

    def __init__(self, host, port, nickname):
        self.speaker = None
        self.audio = None

        # radio hardware interface
        self.radio = hardware.Radio()

        # create the mumble instance
        self.mumble = pymumble.Mumble(host, user=nickname, port=port, debug=False,
                                      certfile='certs/bot.crt', keyfile='certs/bot.key')

        # identify this software
        self.mumble.set_application_string("dmr-bridge")

        # set default callbacks
        self.mumble.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_CONNECTED, self.callback_connected)

        # handle text messages
        self.mumble.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_TEXTMESSAGERECEIVED,
                                           self.callback_received_message)

        # handle incoming audio
        self.mumble.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_SOUNDRECEIVED, self.callback_received_sound)
        self.mumble.set_receive_sound(True)

    def connect(self):
        self.audio = AudioBridge(self.callback_audio)
        self.mumble.start()
        self.mumble.is_ready()
        self.mumble.users.myself.unmute()
        self.set_channel("Radio")
        self.audio.open()

    def connected(self):
        return self.stream.is_active()

    def disconnect(self):
        self.audio.close()

    def set_channel(self, channel):
        c = self.mumble.channels.find_by_name(channel)
        if c:
            c.move_in()

    def callback_audio(self, pcm):
        self.mumble.sound_output.add_sound(pcm)

    def callback_connected(self):
        pass

    def callback_received_message(self, data):
        print("Message: %s" % data.message)

    def callback_received_sound(self, user, chunk):
        # convert to bytes
        self.audio.put(user, chunk.pcm)
