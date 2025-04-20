import os
from typing import Any
import requests
from datetime import datetime
from time import sleep



class GladiaFromFileSTT:
    def __init__(self, api_key:str, file_path: str):
        """
        :param api_key: klucz API
        :param file_path: scieżka pliku do transkrypcji
        """
        self.api_key = api_key
        self.file_path = file_path
        self.base_header = {
            "x-gladia-key": self.api_key,
            "accept": "application/json",
        }

    def makeRequest(self, url, method="GET", data=None, files=None, change_content_type_to_app_json: bool = False) -> requests.Response:
        """
        Wykonuje żądanie HTTP z dynamicznymi nagłówkami.
        :param url: URL żądania
        :param method: Metoda HTTP standardowo GET
        :param data: Dane do wysłania w formacie JSON
        :param files: Pliki do wysłania
        :param change_content_type_to_app_json: Ustawia Content-Type na application/json
        :return: Odpowiedź w formacie JSON
        """
        headers = self.base_header.copy()

        if change_content_type_to_app_json:
            headers["Content-Type"] = "application/json"

        if method == "POST":
            response = requests.post(url, headers=headers, json=data, files=files)
        else:
            response = requests.get(url, headers=headers)

        return response.json()


    @staticmethod
    def getAudioFileForm(file_path) -> list[Any] | None:
        try:
            file_name, file_extension = os.path.splitext(file_path)
            with open(file_path, "rb") as f:
                file_content = f.read()
            audio_file_form = [("audio", (file_path, file_content, "audio/" + file_extension[1:]))]
            return audio_file_form
        except FileNotFoundError as err:
            print(err)
            exit(1)


    def getResultFormRequest(self) -> dict[str, Any] | None:
        upload_response = self.makeRequest("https://api.gladia.io/v2/upload", method="POST",files=self.getAudioFileForm(self.file_path))

        if "audio_url" not in upload_response:
            print(f"Error: Audio URL not found in upload response\nResponse: {upload_response}.")
            exit(1)

        print("Upload response with File ID:", upload_response)

        audio_url = upload_response.get("audio_url")

        data = {
            "audio_url": audio_url,
            "diarization": True,
        }

        post_response = self.makeRequest("https://api.gladia.io/v2/pre-recorded/", "POST", data=data, change_content_type_to_app_json=True)

        print("Sending request to Gladia API...")

        print("Post response with Transcription ID:", post_response)

        result_url = post_response.get("result_url")

        if not result_url:
            print(f"Error: Result URL not found in post response\nResponse: {post_response}.")
            exit(1)
        if result_url:
            return result_url


    def getTranscriptionFormResult(self, result_url) -> dict[str, Any] | None:
        while True:
            poll_response = self.makeRequest(result_url, change_content_type_to_app_json=True)
            status = poll_response.get("status")
            match status:
                case "done":
                    transcription_result = poll_response.get("result")
                    transcription_data = transcription_result.get("transcription", {})

                    if not transcription_data:
                        print("Error: Transcription result not found")
                        break

                    utterance = transcription_data.get("utterances", [])
                    if not utterance:
                        print(f'Warning: No utterances found in transcription data.\nFull transcription: {transcription_data.get("full_transcription", "")}')
                        break
                    return utterance
                case "error":
                    print(f'Transcription failed.\n{poll_response}')
                    break
                case _:
                    print(f'[{datetime.now().strftime("%H:%M:%S")}]Transcription status: {status}.')
            sleep(5)


    @staticmethod
    def showTranscript(utterances) -> None:
        for entry in utterances:
            if isinstance(entry, dict):
                speaker = entry.get("speaker", "Unknown")
                text = entry.get("text", "")
                start = entry.get("start", 0.0)
                end = entry.get("end", 0.0)
                print(f'[{start:06.2f}s - {end:06.2f}s] Speaker {speaker}: {text}')
            else:
                print(f'[Unknown format] {entry}')


    def doTranscription(self):
        result = self.getResultFormRequest()
        utterances = self.getTranscriptionFormResult(result)
        self.showTranscript(utterances)
        input("Press Enter to exit...")


if __name__ == "__main__":
    ob1 = GladiaFromFileSTT("you_wish", "recording.wav")
    ob1.doTranscription()
