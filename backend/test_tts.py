from dotenv import load_dotenv
import os
from elevenlabs.client import ElevenLabs

load_dotenv()
client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])

text = "I can see the menu to your right. Turn slightly right."

audio = client.text_to_speech.convert(
    voice_id="N2lVS1w4EtoT3dr4eOWO",  # a default pre-made voice ElevenLabs provides
    model_id="eleven_multilingual_v2",
    text=text
)

with open("test_output.wav", "wb") as f:
    for chunk in audio:
        f.write(chunk)

print("Saved test_output.wav")