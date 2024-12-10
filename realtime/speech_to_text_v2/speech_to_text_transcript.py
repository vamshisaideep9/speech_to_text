import pyaudio
import wave
import keyboard
import websockets
import asyncio
import io
import base64
from dotenv import dotenv_values
import json

config = dotenv_values()
api_key = config.get("OPENAI_API_KEY")

LOG_EVENT_TYPES = [
    'error', 'response.content.done', 'rate_limits.updated',
    'response.done', 'input_audio_buffer.commit'
]

async def record_audio_to_wav():
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 24000
    CHUNK = 1024

    audio = pyaudio.PyAudio()

    def record():
        try:
            stream = audio.open(format=FORMAT,
                                channels=CHANNELS,
                                rate=RATE,
                                input=True,
                                frames_per_buffer=CHUNK)

            print("\nRecording... Press 'space' to stop.")
            frames = []
            while not keyboard.is_pressed('space'):
                data = stream.read(CHUNK)
                frames.append(data)

            print("\nRecording stopped. Saving file...")

        finally:
            stream.stop_stream()
            stream.close()

        return frames

    frames = await asyncio.to_thread(record)

    output_buffer = io.BytesIO()
    with wave.open(output_buffer, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))

    output_buffer.seek(0)
    return output_buffer.read()

async def initialize_session(openai_ws):
    session_update = {
        "type": "session.updated",
        "session": {
            "turn_detection": {"type": "server_vad"},
            "instructions": "You are a helpful assistant.",
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "voice": "echo",
            "modalities": ["text", "audio"],
            "temperature": 0.7,
            "input_audio_transcription": {
                "enable": True,
                "model": "whisper-1"
            },
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.5,
                "prefix_padding_ms": 300,
                "silence_duration_ms": 500
            }
        }
    }
    print('Sending session update:', json.dumps(session_update))
    await openai_ws.send(json.dumps(session_update))

async def transcript():
    print("Client connected to OpenAI Realtime API")
    uri = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Openai-beta": "realtime=v1"
    }

    while True:
        try:
            async with websockets.connect(uri, extra_headers=headers) as openai_ws:
                await initialize_session(openai_ws)

                async def receive_audio_from_client():
                    try:
                        while True:
                            audio_data = await record_audio_to_wav()
                            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                            audio_event = {
                                "type": "input_audio_buffer.append",
                                "audio": audio_base64
                            }
                            await openai_ws.send(json.dumps(audio_event, indent=2))
                            print("Audio data appended to buffer.")
                            commit_event = {
                                "type": "input_audio_buffer.commit"
                            }
                            await openai_ws.send(json.dumps(commit_event, indent=2))
                            print("Audio buffer committed.")

                    except websockets.exceptions.ConnectionClosed as e:
                        print(f"WebSocket connection closed: {e}")
                        raise

                async def receive_transcription_from_openai():
                    try:
                        async for message in openai_ws:
                            response = json.loads(message)
                            event_type = response.get("type")
                            
                            if event_type == "response.done":
                                # Check that 'output' exists and has content
                                output = response.get('response', {}).get('output', [])
                                if output:
                                    content = output[0].get('content', [])
                                    if content:
                                        transcript = content[0].get('transcript', '')
                                        if transcript:
                                            print(f"Transcription: {transcript}")
                                        else:
                                            print("No transcription found.")
                                    else:
                                        print("Content is empty.")
                                else:
                                    print("No output found in the response.")
                            elif event_type in LOG_EVENT_TYPES:
                                print(f"Event Type: {event_type}, Response: {response}")

                    except websockets.exceptions.ConnectionClosed as e:
                        print(f"WebSocket connection closed: {e}")
                        raise

                # Run both tasks concurrently
                await asyncio.gather(receive_audio_from_client(), receive_transcription_from_openai())

        except websockets.exceptions.ConnectionClosed as e:
            print(f"Connection closed. Retrying... {e}")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Unexpected error: {e}")
            break

asyncio.run(transcript())
