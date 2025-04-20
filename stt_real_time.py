import json
import pyaudio
import websocket
import requests
from threading import Thread, Event
from time import sleep, time

class GladiaRealTimeSTT:
    def __init__(self, api_key: str, on_transcription: callable = None, input_device_index: int = None):
        """
        Inicjalizuje klienta real-time STT z Gladia.
        :param api_key: Gladia API key
        :param on_transcription: Callback wywoływany przy otrzymaniu transkrypcji
        :param input_device_index: Indeks urządzenia wejściowego (opcjonalne)
        """

        self.api_key = api_key
        self.SAMPLE_RATE = 16000  # Hz, wymagane przez Gladia
        self.CHANNELS = 1  # Mono
        self.FORMAT = pyaudio.paInt16  # 16-bit format
        self.CHUNK = 1024  # Rozmiar bufora w próbkach

        self.on_transcription = on_transcription or (lambda text: print(f"Transcription: {text}"))
        self.input_device_index = input_device_index
        self.web_socket = None
        self.audio_stream = None
        self.pyaudio_instance = None
        self.is_running = False
        self.stop_event = Event()  # Event do sygnalizowania zatrzymania wątków
        self.sample_count = 0  # Licznik próbek do debugowania
        self.session_url = None  # URL sesji WebSocket
        self.session_id = None  # ID sesji

        self.headers = {
            "Content-Type": "application/json",
            "X-Gladia-Key": api_key
        }
        self.body = {
            "encoding": "wav/pcm",
            "sample_rate": self.SAMPLE_RATE,
            "bit_depth": 16,
            "channels": self.CHANNELS
        }


    def initializeSession(self):
        """
        Inicjalizuje sesję real-time STT, wysyłając żądanie POST do API Gladia.
        Zwraca URL WebSocket do połączenia.
        """
        print("Initializing real-time STT session...")

        try:
            response = requests.post("https://api.gladia.io/v2/live", headers=self.headers, json=self.body)
            if not response.ok:
                error_text = response.text or response.status_text
                print(f"Error initializing session: {response.status_code}: {error_text}")
                raise ValueError(f"Failed to initialize session: {error_text}")
            data = response.json()
            self.session_id = data.get("id")
            self.session_url = data.get("url")
            print(f"Session initialized. ID: {self.session_id}, URL: {self.session_url}")
            return self.session_url
        except Exception as e:
            print(f"Error initializing session: {e}")
            raise


    def onConnectionOpen(self, ws):
        """
        Wywoływane po otwarciu połączenia WebSocket.
        """
        print("WebSocket connection opened.")
        sleep(1)  # Krótkie opóźnienie przed rozpoczęciem przesyłania audio
        self.startAudioStream()


    def onMessage(self, ws, message):
        """
        Wywoływane przy otrzymaniu wiadomości z WebSocket.
        Przetwarza transkrypcję i wywołuje callback.
        """
        try:
            data = json.loads(message)
            if data.get("type") == "transcript" and "data" in data and "utterance" in data["data"]:
                utterance = data["data"]["utterance"]
                transcription = utterance.get("text", "")
                speaker = data["data"].get("speaker", "Unknown")
                start = utterance.get("start", 0.0)
                end = utterance.get("end", 0.0)
                formatted_text = f'[{start:06.2f}s - {end:06.2f}s] Speaker {speaker}  : {transcription}'
                self.on_transcription(formatted_text)
            elif data.get("type") == "audio_chunk":
                pass
            else:
                pass
        except json.JSONDecodeError:
            print("Error decoding WebSocket message.")


    def onError(self, ws, error):
        """
        Wywoływane przy błędzie WebSocket.
        """
        print(f"WebSocket error: {error}")
        self.stopConnection()


    def onClose(self, ws, close_status_code, close_msg):
        """
        Wywoływane przy zamknięciu połączenia WebSocket.
        """
        print(f"WebSocket connection closed. Status: {close_status_code}, Message: {close_msg}")
        self.stopConnection()


    def startAudioStream(self):
        """
        Rozpoczyna nagrywanie audio z mikrofonu i przesyłanie do WebSocket.
        """
        try:
            self.pyaudio_instance = pyaudio.PyAudio()
            print(f"PyAudio initialized. Available devices: {self.pyaudio_instance.get_device_count()}")

            # Wyświetl listę dostępnych urządzeń audio
            for i in range(self.pyaudio_instance.get_device_count()):
                device_info = self.pyaudio_instance.get_device_info_by_index(i)
                print(f"Device {i}: {device_info['name']}, Input Channels: {device_info['maxInputChannels']}")

            open_params = {
                "format": self.FORMAT,
                "channels": self.CHANNELS,
                "rate": self.SAMPLE_RATE,
                "input": True,
                "frames_per_buffer": self.CHUNK
            }
            if self.input_device_index is not None:
                open_params["input_device_index"] = self.input_device_index
                print(f"Using input device index: {self.input_device_index}")
            self.audio_stream = self.pyaudio_instance.open(**open_params)
            print("Audio stream opened successfully.")
            self.is_running = True
            self.stop_event.clear()  # Resetuje event zatrzymania
            Thread(target=self.streamAudioToWS, daemon=True).start()
        except Exception as e:
            print(f"Error starting audio stream: {e}")
            self.stopConnection()


    def streamAudioToWS(self):
        """
        Przesyła dane audio z mikrofonu do WebSocket w czasie rzeczywistym.
        """
        print("Starting audio streaming...")
        self.sample_count = 0
        while self.is_running and not self.stop_event.is_set():
            try:
                data = self.audio_stream.read(self.CHUNK, exception_on_overflow=False)
                self.sample_count += len(data) // 2  # 2 bajty na próbkę (16-bit)

                if self.sample_count % (self.SAMPLE_RATE * 5) == 0:  # Co 5 sekund
                    print(f"Sent {self.sample_count // self.SAMPLE_RATE} seconds of audio data.")

                if self.is_running and self.web_socket and not self.stop_event.is_set():
                    self.web_socket.send(data, opcode=websocket.ABNF.OPCODE_BINARY)

            except Exception as e:
                print(f'Error streaming audio: {e}')
                self.stopConnection()
                break
        # print("Audio streaming stopped.")


    def startConnection(self):
       """
       Rozpoczyna połączenie WebSocket i nagrywanie audio.
       """
       try:
           print("Initializing real-time STT...")
           self.session_url = self.initializeSession()
           self.is_running = True
           self.web_socket = websocket.WebSocketApp(
               self.session_url,
               header=self.headers,
               on_open=self.onConnectionOpen,
               on_message=self.onMessage,
               on_error=self.onError,
               on_close=self.onClose
           )
           Thread(target=self.web_socket.run_forever, daemon=True).start()

           print("WebSocket thread started.")
           sleep(2)  # Czekamy chwilę na połączenie
           if not self.is_running:
               print("Initialization failed. Stopping...")
               self.stopConnection()
       except Exception as e:
           print(f"Error starting WebSocket: {e}")
           self.stopConnection()


    def stopConnection(self):
       """
       Zamyka połączenie WebSocket i zatrzymuje nagrywanie audio.
       """
       print("Stopping all processes...")
       self.is_running = False
       self.stop_event.set()
       if self.audio_stream:
           try:
               self.audio_stream.stop_stream()
               self.audio_stream.close()
               self.audio_stream = None
               print("Audio stream closed.")
           except Exception as e:
               print(f"Error closing audio stream: {e}")

       if self.pyaudio_instance:
           try:
               self.pyaudio_instance.terminate()
               self.pyaudio_instance = None
               print("PyAudio terminated.")
           except Exception as e:
               print(f"Error terminating PyAudio: {e}")

       if self.web_socket:
           try:
               self.web_socket.close()
               self.web_socket = None
               print("WebSocket closed.")
           except Exception as e:
               print(f"Error closing WebSocket: {e}")
       print("All resources closed.")


    def run(self):
        """
        Główna funkcja do uruchomienia STT
        """

        try:
            print("Starting real-time STT...")
            self.startConnection()
            start_time = time()
            timeout = 120.0
            while self.is_running and (time() - start_time) < timeout:
                sleep(0.5)
                if not self.is_running:
                    print("STT stopped unexpectedly.")
                    break
            if self.is_running:
                print("Timeout. Stopping program...")
                self.stopConnection()
        except KeyboardInterrupt:
            print("Stopped by Ctrl + C...")
            self.stopConnection()
        except Exception as e:
            print(f"Error occurred: {e}")
            self.stopConnection()
        finally:
            self.stopConnection()
            input("Program finished.\nPress enter to exit.")


if __name__ == "__main__":
    ob1 = GladiaRealTimeSTT("you_wish", on_transcription=lambda text: print(text))
    ob1.run()