import os
from dotenv import load_dotenv
from stt_from_file import GladiaFromFileSTT
from stt_real_time import GladiaRealTimeSTT


load_dotenv()

api_key = os.getenv("GLADIA_API_KEY")
if not api_key:
    raise ValueError("GLADIA_API_KEY not found in environment variables.")

if __name__ == "__main__":
    print('Insert "1" to transcript from file, "2" for real time transcript')
    choice = input("Your choice: ")
    match choice:
        case "1":
            from_file = GladiaFromFileSTT(api_key, "recording.wav")
            from_file.doTranscription()
        case "2":
            real_time = GladiaRealTimeSTT(api_key, lambda text: print(text))
            real_time.run()
        case _:
            raise ValueError("Invalid choice")























