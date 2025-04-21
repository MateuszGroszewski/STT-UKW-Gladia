import pyaudio
import wave


class RecordAudio:
    def __init__(self, output_file_path, duration: int = 10, rate: int = 44100, channels: int = 1, chunk: int = 1024 ):
        """
        :param output_file_path:  ścieżka pliku wyjściowego
        :param duration: czas trwania nagrywania
        :param rate: częstotliwość próbkowania w Hz standard 44100 albo 48000
        :param channels: 1 dla mono, 2 dla stereo
        :param chunk: rozmiar buffora
        """

        self.output_file_path = output_file_path
        self.duration = duration
        self.rate = rate
        self.channels = channels
        self.chunk = chunk

    def recordAudio(self):
        audio = pyaudio.PyAudio()

        stream = audio.open(format=pyaudio.paInt16,
                            channels=self.channels,
                            rate=self.rate,
                            input=True,
                            frames_per_buffer=self.chunk)

        print(f'Recording started for {self.duration} seconds')
        frames = []

        for i in range(0, int(self.rate / self.chunk * self.duration)):
            data = stream.read(self.chunk)
            frames.append(data)

        print('Recording ended.')

        stream.stop_stream()
        stream.close()

        audio.terminate()

        with wave.open(self.output_file_path, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
            wf.setframerate(self.rate)
            wf.writeframes(b''.join(frames))

        print(f'Recording save to: {self.output_file_path}')

if __name__ == "__main__":
    ob = RecordAudio("sample.wav", duration=10)
    ob.recordAudio()

