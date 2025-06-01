from dotenv import load_dotenv
import time
import google.generativeai as genai
import os
from config import *


load_dotenv()

if Model not in Models_available:
    raise ValueError("Invalid model specified. Choose either 'gemma-3-27b-it' or 'gemini-1.5-flash'. Or contact Developer to add the model")
elif Model == "gemini-1.5-flash":
    api_key = os.getenv("GEMINI_API_KEY_1_FLASH")
    Calls = Calls_1_Flash
    Period = Period_1_Flash
elif Model =="gemma-3-27b-it":
    api_key = os.getenv("GEMINI_API_KEY_27B_Gemma")
    Calls = Calls_27B_Gemma
    Period = Period_27B_Gemma
# Initialize rate limiter


# --- Manual Rate Limiting Configuration ---
RATE_LIMIT_RPM = Calls # Requests Per Minute
RATE_LIMIT_RPD = Period # Requests Per Day

# Calculate minimum time between requests for RPM
SECONDS_PER_REQUEST_MIN = 60 / RATE_LIMIT_RPM
# Calculate total seconds in a day
SECONDS_PER_DAY = 24 * 60 * 60

# Variables to track API calls for rate limiting
last_request_time = 0.0 # Timestamp of the last API call for RPM
daily_request_count = 0
daily_reset_timestamp = time.time() # When the daily count was last reset (start of current day's window)


# Validate API key
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file.")

# Configure Gemini
genai.configure(api_key=api_key)

LIMIT_KEY = f"{Model}_rate_limit"

# Initialize Gemini model
model = genai.GenerativeModel(Model)
def generate_summary(input_text: str):
    global last_request_time
    global daily_request_count
    global daily_reset_timestamp

    # Daily Limit Check 
    current_time = time.time()
    if current_time - daily_reset_timestamp >= SECONDS_PER_DAY:
        # A new day has started, reset the daily count
        daily_request_count = 0
        daily_reset_timestamp = current_time # Reset the timestamp to the current time

    if daily_request_count >= RATE_LIMIT_RPD:
        # Daily limit exceeded. Calculate remaining time until next day.
        time_to_wait = SECONDS_PER_DAY - (current_time - daily_reset_timestamp)
        print(f"Daily rate limit hit ({RATE_LIMIT_RPD} requests). Waiting until next daily window ({time_to_wait:.2f} seconds)...")
        time.sleep(time_to_wait)
        # After waiting, reset daily count and timestamp
        daily_request_count = 0
        daily_reset_timestamp = time.time() # Update to current time after sleep


    # Minute Limit Check (only if daily limit check passed or was reset)
    current_time = time.time() # Re-check time after potential daily limit sleep
    elapsed_time_since_last_request = current_time - last_request_time

    if elapsed_time_since_last_request < SECONDS_PER_REQUEST_MIN:
        sleep_duration = SECONDS_PER_REQUEST_MIN - elapsed_time_since_last_request
        print(f"Minute rate limit hit. Waiting for {sleep_duration:.2f} seconds...")
        time.sleep(sleep_duration)

    # Update the last request time BEFORE making the actual API call
    last_request_time = time.time()
    daily_request_count += 1 # Increment daily count for this request

    prompt = f"Summarize the following text in a concise paragraph:\n\n{input_text}"
    try:
        response = model.generate_content(prompt)
        # print("\n🔍 Summary:\n") # You might want to print this directly here for debugging
        # print(response.text)
        return response.text
    except Exception as e:
        print(f"Error generating summary: {e}")
        return f"Error: Could not generate summary - {e}"


if __name__ == "__main__":
    generate_summary()

