import numpy as np
import pyaudio
import wave
import queue
from time import sleep, time
from threading import Thread
from noise_reduction import NoiseCancel


class RecordAudio:
    def __init__(self, output_file_path = "default.wav", duration: int = 10, rate: int = 44100, channels: int = 1, chunk: int = 1024, stationary: bool = True, prop_decrease: float = 1.0):
        """
        :param output_file_path:  ścieżka pliku wyjściowego
        :param duration: czas trwania nagrywania
        :param rate: częstotliwość próbkowania w Hz standard 44100 albo 48000
        :param channels: 1 dla mono, 2 dla stereo
        :param chunk: rozmiar buffora
        """

        self.output_file_path: str = output_file_path
        self.duration: int = duration
        self.rate: int = rate
        self.channels: int = channels
        self.chunk: int = chunk

        self.sample_width: int = 0
        self.audio_queue = queue.Queue()
        self.is_running: bool = False
        self.frames: list = []
        self.sample_count: int = 0
        self.noise_profile = None  # Profil szumu do redukcji (ustawiany na początku)

        self.stationary = stationary
        self.prop_decrease = prop_decrease

        self.audio = pyaudio.PyAudio()
        self.stream = self.stream = self.audio.open(format=pyaudio.paInt16,
                            channels=self.channels,
                            rate=self.rate,
                            input=True,
                            frames_per_buffer=self.chunk)


    @staticmethod
    def listAudioDevices() -> None:
        """
        Wyświetla listę dostępnych urządzeń audio.
        """
        p = pyaudio.PyAudio()
        print(f"Available audio devices: {p.get_device_count()}")
        for i in range(p.get_device_count()):
            device_info = p.get_device_info_by_index(i)
            print(f"Device {i}: {device_info['name']}, Input Channels: {device_info['maxInputChannels']}")
        p.terminate()


    def recordNormalAudio(self):
        print(f'Recording started for {self.duration} seconds')

        for i in range(0, int(self.rate / self.chunk * self.duration)):
            data = self.stream.read(self.chunk)
            self.frames.append(data)

        print('Recording ended.')

        self.stream.stop_stream()
        self.stream.close()

        self.audio.terminate()

        self.stopRecording()


    def recordToQueue(self):
        """
        Nagrywa audio do kolejki
        """
        start_time = time()

        while self.is_running and time() - start_time < self.duration:
            try:
                data = self.stream.read(self.chunk, exception_on_overflow=False)
                self.audio_queue.put(data)
            except Exception as e:
                print(f'Error occurred: {e}')
                self.stopRecording()
                break
        self.stopRecording()


    def stopRecording(self):

        """
        Zatrzymuje nagrywanie i zapisuje przetworzone dane do pliku WAV.
        """
        print("Stopping recording..")
        self.is_running = False
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
                print("Audio stream closed.")
            except Exception as e:
                print(f"Error closing audio stream: {e}")
        if self.audio:
            try:
                self.sample_width = self.audio.get_sample_size(pyaudio.paInt16)
                self.audio.terminate()
                self.audio = None
                print("PyAudio terminated.")
            except Exception as e:
                print(f"Error terminating PyAudio: {e}")

        while not self.audio_queue.empty():
            sleep(0.1)

        if self.frames:
            try:
                with wave.open(self.output_file_path, 'wb') as wf:
                    wf.setnchannels(self.channels)
                    wf.setsampwidth(self.sample_width)
                    wf.setframerate(self.rate)
                    wf.writeframes(b''.join(self.frames))
                print(f'Recording save to: {self.output_file_path}')
            except Exception as e:
                print(f"Error occurred while trying to save: {e}")
        else:
            print(f'No audio to save')


    def processAudio(self):
        temp = NoiseCancel(stationary=self.stationary, prop_decrease=self.prop_decrease)

        while self.is_running or not self.audio_queue.empty():
            try:
                data = self.audio_queue.get(timeout=1.0)
                audio_data = np.frombuffer(data, dtype=np.int16)

                if len(audio_data) > 0:
                    self.sample_count += len(audio_data)
                    if self.noise_profile is None and self.sample_count < (self.rate * temp.noise_clip_duration):
                        print(f"Collecting noise profile... ({self.sample_count}/{int(self.rate * temp.noise_clip_duration)} samples)")
                        if self.noise_profile is None:
                            self.noise_profile = audio_data
                        else:
                            self.noise_profile = np.concatenate((self.noise_profile, audio_data))
                    else:
                        if self.noise_profile is not None:
                            processed_data = temp.realTimeReduction(audio_data=audio_data, rate=self.rate, noise_profile=self.noise_profile)
                            self.frames.append(processed_data)
                        else:
                            self.frames.append(data)
                self.audio_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f'Error occurred : {e}')
                break


    def recordWithNoiseReduction(self):
        self.is_running = True
        print(f"Recording started for {self.duration} seconds... Speak now!")
        Thread(target=self.recordToQueue, daemon=True).start()
        Thread(target=self.processAudio, daemon=True).start()
        sleep(self.duration+2)


if __name__ == "__main__":
    ob = RecordAudio(duration=10, prop_decrease=1.5)
    ob.recordWithNoiseReduction()


# if __name__ == "__main__":
#     ob = RecordAudio("sampler.wav", duration=10, prop_decrease=1.5)
#     ob.recordNormalAudio()

