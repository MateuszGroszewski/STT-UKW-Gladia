import os
from dotenv import load_dotenv
from stt_from_file import GladiaFromFileSTT
from stt_real_time import GladiaRealTimeSTT
from noise_reduction import NoiseCancel
from recording import RecordAudio


load_dotenv()

api_key = os.getenv("GLADIA_API_KEY")
if not api_key:
    raise ValueError("GLADIA_API_KEY not found in environment variables.")

if __name__ == "__main__":
    print('Insert "1" to transcript from file, "2" for real time transcript, "3" for recording audio, "4" for reducing noise in existing file "5" recording audio with noise reduction')
    choice = input("Your choice: ")
    match choice:
        case "1":
            from_file = GladiaFromFileSTT(api_key, "recording.wav")
            from_file.doTranscription()
        case "2":
            real_time = GladiaRealTimeSTT(api_key, lambda text: print(text))
            real_time.run()
        case "3":
            record = RecordAudio("sample.wav")
            record.recordNormalAudio()
        case "4":
            noise_cancel = NoiseCancel("sample.wav", "denoised.wav")
            noise_cancel.applyNoiseReduction()
        case "5":
            record_with_noise_reduction  = RecordAudio("sample.wav", duration=15, prop_decrease=0.5)
            record_with_noise_reduction.recordWithNoiseReduction()
        case _:
            raise ValueError("Invalid choice")























