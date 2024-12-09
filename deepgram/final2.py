from dotenv import load_dotenv
from deepgram import (
    DeepgramClient,
    LiveTranscriptionEvents,
    LiveOptions,
    Microphone,
)

load_dotenv()
speaker_transcripts = {}

def main():
    try:
        deepgram: DeepgramClient = DeepgramClient()
        dg_connection = deepgram.listen.websocket.v("1")

        def on_open(self, open, **kwargs):
            print("Connection Open")

        def on_message(self, result, **kwargs):
            global speaker_transcripts
            if result.is_final: 
                words = result.channel.alternatives[0].words
                if words:
                    for word_info in words:
                        word = word_info.word
                        speaker = word_info.speaker
                        if word:
                            if speaker not in speaker_transcripts:
                                speaker_transcripts[speaker] = []
                            speaker_transcripts[speaker].append(word)
            
                for speaker, transcript in speaker_transcripts.items():
                    print(f"Speaker {speaker}: {' '.join(transcript)}")
                speaker_transcripts.clear()

        def on_close(self, close, **kwargs):
            print("Connection Closed")

        def on_error(self, error, **kwargs):
            print(f"Handled Error: {error}")

        dg_connection.on(LiveTranscriptionEvents.Open, on_open)
        dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
        dg_connection.on(LiveTranscriptionEvents.Close, on_close)
        dg_connection.on(LiveTranscriptionEvents.Error, on_error)

        options: LiveOptions = LiveOptions(
            model="nova-2",
            language="en-us",
            smart_format=True, #can automatically format transcripts to improve redability
            encoding="linear16", #16-bit encoding
            channels=1, #mono
            sample_rate=16000, #no of samples of audio data captured per second. (hertz)
            interim_results=True, #Provides preliminary results for streaming audio
            utterance_end_ms="1000", #can be useful to detect the end of speech.
            vad_events=True, #This enables voice activity detection, which detects when speech starts and stops
            endpointing=1000, #returns transcript when pauses in speech are detected
            diarize=True, #Recognizes speaker changes and assign a speaker to each word in the transcript
            punctuate=True, #Adds punctuation and captalization
            filler_words=False
            
            
        )

        addons = {"no_delay": "true"}

        print("\n\nPress Enter to stop recording...\n\n")
        if dg_connection.start(options, addons=addons) is False:
            print("Failed to connect to Deepgram")
            return
        microphone = Microphone(dg_connection.send)
        microphone.start()
        input("")
        microphone.finish()
        dg_connection.finish()

        print("Finished")

    except Exception as e:
        print(f"Could not open socket: {e}")
        return


if __name__ == "__main__":
    main()


"""
https://github.com/deepgram/deepgram-python-sdk/tree/main?tab=readme-ov-file#live-audio-transcription-quickstart
"""