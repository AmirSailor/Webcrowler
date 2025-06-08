from dotenv import load_dotenv
import time
import google.generativeai as genai
import os
import sys # For printing errors to stderr

# Load environment variables from .env file
load_dotenv()

# Module-level variables for API client and rate limiting.
# These are initialized once by setup_summarizer().
_gemini_model = None
_selected_model_name = ""
_rate_limit_rpm = 0
_rate_limit_period = 0 # This represents requests per day in your config
_seconds_per_request_min = 0.0
_seconds_per_day = 24 * 60 * 60 # Constant for daily rate limit calculations

# Variables to track API calls for rate limiting across multiple calls within a run
_last_request_time = 0.0
_daily_request_count = 0
_daily_reset_timestamp = time.time() # Resets on each script run


def setup_summarizer(config: dict):
    
    global _gemini_model, _selected_model_name, _rate_limit_rpm, _rate_limit_period, _seconds_per_request_min

    # Retrieve API settings from the config dictionary
    api_settings = config.get('api_settings', {})
    _selected_model_name = api_settings.get('default_model')
    available_models = api_settings.get('available_models', [])

    if not _selected_model_name or _selected_model_name not in available_models:
        print(f"Error: Invalid or missing 'default_model' ('{_selected_model_name}') in config.yml.", file=sys.stderr)
        print(f"Available models specified: {', '.join(available_models)}. Please correct your config.yml.", file=sys.stderr)
        sys.exit(1)

    api_key = None
    model_config = api_settings.get(_selected_model_name.replace('-', '_'), {}) # e.g., 'gemini_1_5_flash'

    if _selected_model_name == "gemini-1.5-flash":
        api_key = os.getenv("GEMINI_API_KEY_1_FLASH")
    elif _selected_model_name == "gemma-3-27b-it":
        api_key = os.getenv("GEMINI_API_KEY_27B_Gemma")

    if not api_key:
        print(f"Error: API key for model '{_selected_model_name}' not found in your .env file.", file=sys.stderr)
        print("Ensure you have 'GEMINI_API_KEY_1_FLASH' or 'GEMINI_API_KEY_27B_GEMMA' set.", file=sys.stderr)
        sys.exit(1)

    genai.configure(api_key=api_key)
    _gemini_model = genai.GenerativeModel(_selected_model_name)

    _rate_limit_rpm = model_config.get('calls_per_minute', 15)
    _rate_limit_period = model_config.get('period_milliseconds', 14400) # Assuming this is intended for daily calls

    # Calculate minimum time between requests to respect RPM
    _seconds_per_request_min = 60 / _rate_limit_rpm if _rate_limit_rpm > 0 else 0


def generate_summary(input_text: str) -> str:
    """
    Generates a concise summary of the provided text using the configured Gemini model.
    It incorporates rate limiting to respect API usage policies.
    """
    # Ensure the summarizer has been initialized
    if _gemini_model is None:
        print("Error: Summarizer has not been initialized. Call setup_summarizer() first.", file=sys.stderr)
        return "Summary Error: Summarizer not configured."

    global _last_request_time, _daily_request_count, _daily_reset_timestamp

    current_time = time.time()

    # Handle daily rate limit reset
    if current_time - _daily_reset_timestamp >= _seconds_per_day:
        _daily_request_count = 0
        _daily_reset_timestamp = current_time

    # Enforce daily rate limit
    if _daily_request_count >= _rate_limit_period:
        wait_duration = _seconds_per_day - (current_time - _daily_reset_timestamp)
        print(f"Daily API limit reached for model '{_selected_model_name}'. Waiting {wait_duration:.2f} seconds until next daily window.", file=sys.stderr)
        time.sleep(wait_duration)
        _daily_request_count = 0
        _daily_reset_timestamp = time.time() # Reset timestamp after waiting

    # Re-evaluate current time after potential daily limit sleep
    current_time = time.time()
    elapsed_time = current_time - _last_request_time

    # Enforce per-minute rate limit
    if elapsed_time < _seconds_per_request_min:
        sleep_needed = _seconds_per_request_min - elapsed_time
        print(f"Per-minute API limit for '{_selected_model_name}'. Waiting {sleep_needed:.2f} seconds.", file=sys.stderr)
        time.sleep(sleep_needed)

    # Update state for next API call
    _last_request_time = time.time()
    _daily_request_count += 1

    prompt = f"Summarize the following text in a concise paragraph:\n\n{input_text}"
    try:
        response = _gemini_model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error generating summary with model '{_selected_model_name}': {e}", file=sys.stderr)
        return f"Summary Error: Failed to generate summary - {e}"
