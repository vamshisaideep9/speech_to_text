import openai
import pyaudio
import numpy as np
import wave
import time
from dotenv import dotenv_values

config = dotenv_values()

openai.api_key = config.get("OPENAI_API_KEY")

# Parameters for PyAudio
FORMAT = pyaudio.paInt16 
CHANNELS = 1  
RATE = 16000  
CHUNK = 1024  
FORMAT = pyaudio.paInt16
RECORD_SECONDS = 5  
p = pyaudio.PyAudio()
def record_audio():
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    
    print("Recording...")
    frames = []
    
    for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):  
        data = stream.read(CHUNK)
        frames.append(data)
    
    print("Finished recording")
    stream.stop_stream()
    stream.close()
    
    return b''.join(frames)

def transcribe_audio():
    while True:
        audio_data = record_audio()
        transcription = openai.audio.transcriptions.create(
            model="whisper-1",
            file=audio_data,
            language="en"
        )
        
        print("Transcription:", transcription['text'])
        time.sleep(1)  
transcribe_audio()

"""
Problem: 
Whisper api does not support realtime audio. Supports only audio from files
like, mp3, mp4, mpeg, ogg, wav etc...

"""