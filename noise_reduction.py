import numpy as np
import soundfile as sf
import noisereduce as nr

class NoiseCancel:
    def __init__(self, file_path = None, output_file_path = None, noise_clip_duration: float = 0.5, stationary: bool = True, prop_decrease: float = 1.0):
        """
        Możesz eksperymentować z parametrami:
            - Zwiększ noise_clip_duration jeśli masz dłuższy fragment czystego szumu.
            - Zmień stationary na False dla bardziej złożonych szumów, ale może wymagać większych zasobów.
            - Zmniejsz prop_decrease (np. 0.8) jeśli pełne tłumienie zbyt mocno wpływa na mowę.
        """

        self.file_path = file_path
        self.output_file_path = output_file_path
        self.noise_clip_duration = noise_clip_duration
        self.stationary = stationary
        self.prop_decrease = prop_decrease


    def applyNoiseReduction(self):
        try:
            if self.file_path is None or self.output_file_path is None:
                raise ValueError("There is no file_path or output_file_path")

            data, rate = sf.read(self.file_path)

            if data.dtype != np.float32 and data.dtype != np.float64:
                print(f'Warning! Data conversion from {data.dtype} to float32.')
                data = data.astype(np.float32)

            noise_len = int(self.noise_clip_duration * rate)
            if noise_len == 0 or noise_len > data.shape[0]:
                print('Error incorrect noise length.')
                return

            noise_sample = data[:noise_len]

            denoised_data = nr.reduce_noise(y=data,
                                            sr=rate,
                                            y_noise=noise_sample,
                                            stationary=self.stationary,
                                            prop_decrease=self.prop_decrease)

            sf.write(self.output_file_path, denoised_data, rate)
            print(f'Noise reduced and save to: {self.output_file_path}')

        except FileNotFoundError:
            print(f'File not found: {self.file_path}')

        except Exception as e:
            print(f'Error occurred: {e}')



    def realTimeReduction(self, audio_data, rate, noise_profile):
        audio_after_reduction = nr.reduce_noise(
            y=audio_data,
            sr=rate,
            y_noise=noise_profile[:len(audio_data)],
            stationary=self.stationary,
            prop_decrease=self.prop_decrease
        )

        return audio_after_reduction.astype(np.int16).tobytes()



if __name__ == "__main__":
    ob = NoiseCancel("sample2.wav", "denoised.wav", noise_clip_duration=1.0, stationary=True, prop_decrease=0.5)
    ob.applyNoiseReduction()

