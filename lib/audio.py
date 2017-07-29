""" This library contains audio utilities """
import numpy as np
import queue
import pyaudio
import lib.hardware as hardware
import threading


class AudioBuffer:
    def __init__(self, dtype, size):
        self.lock = threading.Lock()
        self.buffer = np.zeros(size, dtype=dtype)
        self.dtype = dtype
        self.write_p = 0
        self.read_p = 0
        self.avail = 0
        self.active = False

    def empty(self):
        return self.avail <= 0

    def put(self, array):
        self.lock.acquire()
        if self.avail + len(array) > len(self.buffer):
            self.lock.release()
            return

        if self.write_p + len(array) < len(self.buffer):
            self.buffer[self.write_p:][:len(array)] = array
        else:
            len_end = len(self.buffer) - self.write_p
            len_begin = len(array) - len_end
            self.buffer[self.write_p:][:len_end] = array[:len_end]
            self.buffer[:len_begin] = array[len_end:]

        self.avail = self.avail + len(array)
        self.write_p = (self.write_p + len(array)) % len(self.buffer)
        self.lock.release()

    def get(self, frame_count, hold=False):
        self.lock.acquire()
        if hold or self.avail == 0:
            self.lock.release()
            return np.zeros(frame_count, dtype=self.dtype)

        if self.avail < frame_count:
            self.lock.release()
            return self.fill(frame_count)

        self.active = True
        ret = np.roll(self.buffer, -self.read_p)[:frame_count]
        self.read_p = (self.read_p + frame_count) % len(self.buffer)
        self.avail = self.avail - frame_count
        self.lock.release()
        return ret

    def fill(self, frame_count):
        filling = np.zeros(frame_count - self.avail, dtype=self.dtype)
        if self.active:
            self.active = False
            return np.append(self.get(self.avail), filling)
        else:
            self.active = True
            return np.append(filling, self.get(self.avail))

    @staticmethod
    def test():
        print("Testing class AudioBuffer")
        frame_count = 4

        buffer = AudioBuffer(dtype=np.int16, size=20)
        print("Zero buffer: %s" % (buffer.get(frame_count)))

        buffer.put(np.array(range(0, 10), dtype=np.int16))

        for i in range(1, 3):
            print("Part %d: %s" % (i, buffer.get(frame_count)))

        buffer.put(np.array(range(0, 8), dtype=np.int16))
        buffer.put(np.array(range(0, 8), dtype=np.int16))

        for i in range(1, 6):
            print("Part %d: %s" % (i, buffer.get(frame_count)))


class AudioBridge:
    """ Bridge Audio """
    AUDIO_FRAME = 16384
    AUDIO_BUFFER = AUDIO_FRAME * 20

    def __init__(self, callback):
        self.callback_bridge_audio = callback
        self.output_buffer = AudioBuffer(dtype=np.int16, size=AudioBridge.AUDIO_BUFFER)
        self.hardware = hardware.Radio()

        # radio state and buffer
        self.radio_buffer = b''
        self.radio_state = 0

        # open audio interface
        self.p = pyaudio.PyAudio()
        self.voice_detection = VoiceDetector()

        self.stream = self.p.open(format=self.p.get_format_from_width(2),
                                  channels=1,
                                  rate=48000,
                                  input=True,
                                  output=True,
                                  stream_callback=self.callback_process_audio,
                                  frames_per_buffer=AudioBridge.AUDIO_FRAME)

    def open(self):
        self.stream.start_stream()

    def close(self):
        self.stream.stop_stream()

    def callback_process_audio(self, in_data, frame_count, time_info, status):
        # put audio into voice detector
        self.voice_detection.put(in_data)

        # received audio from voice detector
        pcm = self.voice_detection.get()

        if pcm:
            self.callback_bridge_audio(pcm)

        if not self.output_buffer.empty():
            self.hardware.talk()
        else:
            self.hardware.release()

        # copy buffered mumble input buffer to radio output
        return self.output_buffer.get(frame_count, hold=(not self.hardware.is_ready())), pyaudio.paContinue

    def put(self, pcm):
        self.output_buffer.put(np.fromstring(pcm, dtype=np.int16))


class VoiceDetector:
    """ This class accepts audio and indicates if voice is detected """

    def __init__(self):
        # state for voice activation
        self.state = {
            'level': 0.0,
            'count': 0,
            'maxcount': 3,
            'activation_level': np.iinfo(np.uint16).max * 0.6
        }

        self.queue = queue.Queue()

    def put(self, pcm):
        try:
            self.queue.put(pcm, True)
        except queue.Full:
            pass

    def get(self):
        try:
            return self.queue.get(False)
        except queue.Empty:
            return None

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


if __name__ == "__main__":
    AudioBuffer.test()
