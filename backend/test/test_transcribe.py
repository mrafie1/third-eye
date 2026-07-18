from dotenv import load_dotenv
import os
from google import genai

load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

audio_file = client.files.upload(file="test_transcribe.wav")

response = client.models.generate_content (
    model="gemini-flash-latest",
    contents=[
        "Transcribe this audio exactly. Return only spoken words, nothing else.",
        audio_file
    ]
)

print(response.text)