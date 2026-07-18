from dotenv import load_dotenv
import os
from google import genai

load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

image_file = client.files.upload(file="test_menu.jpg")

prompt = """
You are a visual assistant for a blind or low-vision user wearing a camera.
The user asked: "Can you help me find the menu?"

Respond with a short, direct answer describing where the object is
relative to the center of the image (left, right, up, down, or centered),
and whether it's visible at all. If you're not confident, say so.
"""

response = client.models.generate_content(
    model="gemini-flash-latest",
    contents=[prompt, image_file]
)

print(response.text)