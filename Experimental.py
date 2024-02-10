import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GOOGLE_AI_KEY = os.getenv("GOOGLE_AI_KEY")
genai.configure(api_key=GOOGLE_AI_KEY)

model = genai.GenerativeModel("gemini-pro")

response = model.generate_content("What is flush when printing a string in python?", stream=True)

for chunk in response:
    print(chunk.text, end='')

print(response.prompt_feedback)