import asyncio
import json
import pyaudio
import websockets
import numpy as np
from dotenv import dotenv_values
config = dotenv_values()
API_KEY = config.get("OPENAI_API_KEY")

if not API_KEY:
    raise ValueError("Missing OpenAI API key. Set it in your environment variables.")

URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "OpenAI-Beta": "realtime=v1",
}

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK_SIZE = 1024

async def record_audio():
    p = pyaudio.PyAudio()
    try:
        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK_SIZE)
        print("Audio stream successfully opened.")
    except Exception as e:
        print("Failed to open audio stream:", e)
        return

    print("Recording audio...")
    try:
        while True:
            try:
                data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
                yield data
            except Exception as e:
                print("Error capturing audio:", e)
                break
    finally:
        print("Closing audio stream.")
        stream.stop_stream()
        stream.close()
        p.terminate()
        
async def transcribe_audio():
    try:
        async with websockets.connect(URL, extra_headers=HEADERS) as ws:
            print("Connected to WebSocket.")
            session_event = {
                "type": "session.update",
                "session": {
                    "modalities": [ "text"],
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "input_audio_transcription": {
                        "model": "whisper-1"
                    }
                },
            }
            await ws.send(json.dumps(session_event))
            print("Session initialized.")

        async for audio_data in record_audio():
            audio_event = {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_audio", "input_audio_format": "pcm16", "audio": audio_data}]
                },
            }
            await ws.send(json.dumps(audio_event))
            print("Audio sent to server.")

            while True:
                try:
                    response = await ws.recv()
                    data = json.loads(response)
                    print("Response from server:", data)  

                    if data["type"] == "conversation.item.input_audio_transcription.completed":
                        transcript = data.get("transcript", "")
                        item_id = data.get("item_id", "")
                        content_index = data.get("content_index", 0)
        
                        print(f"Transcription completed for item {item_id} (content index {content_index}):")
                        print(f"Transcript: {transcript}")
                except json.JSONDecodeError as e:
                    print("JSON decoding error:", e)
                except websockets.exceptions.ConnectionClosed as e:
                    print("WebSocket connection closed unexpectedly:", e)
                    return
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"Connection failed with status code: {e.status_code}")
    except Exception as e:
        print("Unexpected error:", e)
asyncio.run(transcribe_audio())


"""
RealTime api mainly focuses on speech to speech/ text to speech/ text to text

1. using Realtime api, It cannot convert to text from the audio directly from mic.  ---- It is possible, test it now
2. converting from speech to text:
   a. The audio from the mic should be stored in files (.wav) - 
   b. Then, we can convert that speech to text using whisper-1
   c. Even whisper-1 does not accept audio from mic. - Use realtime-whisper



check realtimeapi document:
https://platform.openai.com/docs/guides/realtime?text-generation-quickstart-example=stream#input-and-output-transcription


We can use Input audio buffer
https://platform.openai.com/docs/api-reference/realtime-client-events/input_audio_buffer


*** Even after transcription through realtime and wishper-1 its not possible for diarization.

"""
