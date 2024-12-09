import numpy as np  
import base64

def float_to_16bit_pcm(float32_array):
    clipped = np.clip(float32_array, -1, 1)
    pcm16 = (clipped*32767).astype(np.int16)
    return pcm16.tobytes()


def base64_encode_audio(float32_array):
    pcm16_data = float_to_16bit_pcm(float32_array)
    return base64.b64encode(pcm16_data).decode("utf-8")
