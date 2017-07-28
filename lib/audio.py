""" This library contains audio utilities """
import numpy as np


class AudioBuffer:
    def __init__(self, dtype, size):
        self.buffer = np.zeros(size, dtype=dtype)
        self.dtype = dtype
        self.write_p = 0
        self.read_p = 0
        self.avail = 0
        self.hold = False
        self.active = False

    def put(self, array):
        if self.avail + len(array) > len(self.buffer):
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

    def get(self, frame_count):
        if self.hold:
            return np.zeros(frame_count, dtype=self.dtype)

        if self.avail < frame_count:
            return self.fill(frame_count)

        self.active = True
        ret = np.roll(self.buffer, -self.read_p)[:frame_count]
        self.read_p = (self.read_p + frame_count) % len(self.buffer)
        self.avail = self.avail - frame_count
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
        buffer.hold = True

        for i in range(1, 3):
            print("Part %d: %s" % (i, buffer.get(frame_count)))

        buffer.hold = False

        for i in range(1, 3):
            print("Part %d: %s" % (i, buffer.get(frame_count)))

        buffer.put(np.array(range(0, 8), dtype=np.int16))
        buffer.put(np.array(range(0, 8), dtype=np.int16))

        for i in range(1, 6):
            print("Part %d: %s" % (i, buffer.get(frame_count)))

if __name__ == "__main__":
    AudioBuffer.test()
