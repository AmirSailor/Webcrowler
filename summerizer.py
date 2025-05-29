from dotenv import load_dotenv
import base64
import google.generativeai as genai
from google.genai import types

import os
example_txt = "Gisma University of Applied Sciences | Study in Germany From $400 to a Thriving Brand: How Gisma Student Linna Is Turning Business Theory Into Real-World Success watch linna's story Degrees Designed to Create Impact Explore a dynamic range of undergraduate and postgraduate programmes across business, engineering, and technology. Undergraduate Get ready to thrive in the workplace with an immersive bachelor’s degree. You’ll also get access to a dedicated career support team that will help you find your dream job."
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# Validate API key
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file.")

# Configure Gemini
genai.configure(api_key=api_key)

# Initialize Gemini model
model = genai.GenerativeModel('gemini-1.5-flash')
def generate_summary(input_text: str):
    prompt = f"Summarize the following text in a concise paragraph:\n\n{input_text}"
    response = model.generate_content(prompt)
    print("\n🔍 Summary:\n")
    print(response.text)


if __name__ == "__main__":
    input_text = example_txt
    generate_summary(input_text)


