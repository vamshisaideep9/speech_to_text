import pyaudio
import wave
import keyboard
import asyncio
import openai
import tempfile
from dotenv import dotenv_values

# Load OpenAI API key
config = dotenv_values()
api_key = config.get("OPENAI_API_KEY")
openai.api_key = api_key

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

    # Save to a temporary WAV file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    with wave.open(temp_file, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))

    temp_file.close()
    audio.terminate()
    return temp_file.name  


async def transcribe_audio(audio_file_path):
    try:
        with open(audio_file_path, 'rb') as audio_file:
            transcription = openai.audio.transcriptions.create( 
                model="whisper-1",
                file=audio_file
            )
        print("Transcription:")
        print(transcription.text) 
    except Exception as e:
        print("Error during transcription:", e)


async def main():
    audio_file_path = await record_audio_to_wav()
    await transcribe_audio(audio_file_path)

if __name__ == "__main__":
    asyncio.run(main())





"""
Problem: 
Whisper api does not support realtime audio. Supports only audio from files
like, mp3, mp4, mpeg, ogg, wav etc...

"""