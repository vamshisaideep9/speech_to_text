import pyaudio
import asyncio
import websockets
import json
import threading
from dotenv import dotenv_values

config = dotenv_values()


DEEPGRAM_API_KEY = config.get("DEEPGRAM_API_KEY")

FORMAT = pyaudio.paInt16  # 16-bit audio
CHANNELS = 1              # Mono audio
RATE = 44100              # Sampling rate
CHUNK = 3500              # Audio chunk size

DEEPGRAM_WS_URL = f"wss://api.deepgram.com/v1/listen?diarize=true&punctuate=true&utterances=true&encoding=linear16&keywords=KEYWORD:INTENSIFIER&sample_rate={RATE}&channels={CHANNELS}"

stop_flag = threading.Event()

async def send_audio(ws, stream):
    print("Streaming audio to Deepgram...")
    try:
        while not stop_flag.is_set():
            data = stream.read(CHUNK, exception_on_overflow=False)
            if data:
                await ws.send(data)
    except Exception as e:
        print(f"Error streaming audio: {e}")
    finally:
        await ws.send(json.dumps({"type": "CloseStream"}))
        print("Audio stream closed.")


async def receive_transcriptions(ws):
    print("Receiving transcriptions...")
    try:
        async for message in ws:
            response = json.loads(message)
            if "words" in response["channel"]["alternatives"][0]:
                speaker_text = {}
                for word_info in response["channel"]["alternatives"][0]["words"]:
                    word = word_info.get('word', '')
                    speaker = word_info.get('speaker', 'Unknown')
                    if word:
                        if speaker not in speaker_text:
                            speaker_text[speaker] = []  
                        speaker_text[speaker].append(word)
                for speaker, words in speaker_text.items():
                    print(f"Speaker {speaker}: {' '.join(words)}")

    except Exception as e:
        print(f"Error receiving transcriptions: {e}")

async def stream_audio_to_deepgram():
    try:
        options = {
            "type": "Configure",
            "features": {
                "model": "nova-2",
                "language": "en-US",
                "diarize": True,
                "smart_format": True,
                "punctuate": True
            }
        }

        async with websockets.connect(
            DEEPGRAM_WS_URL,
            extra_headers={"Authorization": f"Token {DEEPGRAM_API_KEY}",
                           "content-type": "audio/mp3"}  
        ) as ws:
            print("Connected to Deepgram WebSocket")
            await ws.send(json.dumps(options))
            audio = pyaudio.PyAudio()
            stream = audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK
            )
            await asyncio.gather(send_audio(ws, stream), receive_transcriptions(ws))
            stream.stop_stream()
            stream.close()
            audio.terminate()
            print("Audio resources cleaned up.")
    except Exception as e:
        print(f"Error: {e}")

def main():
    loop = asyncio.new_event_loop()
    threading.Thread(target=loop.run_until_complete, args=(stream_audio_to_deepgram(),), daemon=True).start()
    input("Press Enter to stop transcription...\n")
    stop_flag.set()
    print("Stopping transcription...")

if __name__ == "__main__":
    main()

