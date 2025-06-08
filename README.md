# 🕸️ Configurable Multi-Threaded Web Crawler
A robust, multi-threaded web crawler designed for efficient data extraction from websites. This crawler allows you to configure target URLs, crawling behavior, data parsing, and even integrates with AI models for content summarization, all managed through a simple YAML configuration file.

# ✨ Features
Multi-threaded Crawling: Utilizes multiple threads for faster concurrent page fetching.
Dynamic Configuration: All core settings (homepage URL, project name, thread count, exclusions, API details) are managed via config.yml.
Robots.txt Adherence: Automatically checks and respects robots.txt rules to ensure ethical crawling.
User-Agent Rotation & Delays: Uses a list of user agents and implements random delays to mimic human Browse behavior and avoid blocking.
Intelligent Content Parsing:
Removes unwanted HTML tags and CSS classes specified in config.yml to clean extracted text.
Attempts to extract publication dates using multiple strategies (HTML time tags, common classes, meta tags, regex patterns).
AI-Powered Summarization: Integrates with Google Gemini API to summarize extracted page content (optional, configurable via config.yml).
SQLite Data Storage: Stores crawled page URLs, titles, cleaned text, dates, and summaries in a local SQLite database for easy access.
Persistent State: Maintains queue.txt and crawled.txt files to resume crawling if interrupted.
🚀 Getting Started
Follow these steps to get your crawler up and running.

Prerequisites
Python 3.8+
pip (Python package installer)
Installation
Clone the repository:

Bash

git clone https://github.com/AmirSailor/Webcrowler.git
cd Webcrowler

Install dependencies:

Bash

pip install -r requirements.txt


Configuration
The crawler is highly configurable via two main files:

config.yml: This file contains all the crawler's operational settings.

Create a file named config.yml in the root directory of your project.
Populate it with your desired settings. Here's an example:

YAML

# Crawler Configuration

# Project and Target Settings
project_name: MyAwesomeCrawler 
homepage_url: https://www.example.com/
domain_name: example.com 

# Exclusions for Content Parsing
exclude_tags:
  - nav
  - script
  - style
  - header
  - footer
  - figure
exclude_classes:
  - header__inner
  - social-share__title
  - footer f156hidz
  # ... add more classes to exclude ...

# Data Extraction Features
summary_mode: True # Set to 'true' to enable AI summarization of content

# Performance Settings
number_of_threads: 8 # Number of concurrent crawling threads

# Anti-Blocking Measures
min_delay_seconds: 1.5 # Minimum random delay between requests
max_delay_seconds: 4.0 # Maximum random delay between requests
user_agents: # List of User-Agent strings to rotate through
  - "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
  - "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
  # ... add more user agents ...

# API/Model Settings (for content summarization via Google Gemini)
api_settings:
  default_model: gemma-3-27b-it # Choose 'gemini-1.5-flash' or 'gemma-3-27b-it'
  available_models:
    - gemini-1.5-flash
    - gemma-3-27b-it
  gemini_1_5_flash:
    calls_per_minute: 15
    period_milliseconds: 500 # Daily request limit (e.g., 500 requests per day)
  gemma_3_27b_it:
    calls_per_minute: 15
    period_milliseconds: 14400 # Daily request limit (e.g., 14400 requests per day)

# Database Settings
database_filename: scraped_data.db # Name of the SQLite database file
.env file: This file securely stores your API keys.

Create a file named .env in the root directory of your project.
Add your Gemini API keys to this file. Do not commit this file to public repositories!
Code snippet

GEMINI_API_KEY_1_FLASH="YOUR_GEMINI_1_5_FLASH_API_KEY_HERE"
GEMINI_API_KEY_27B_GEMMA="YOUR_GEMINI_GEMMA_API_KEY_HERE"
(Replace the placeholder values with your actual API keys obtained from Google AI Studio).

🏃‍♀️ Usage
Once configured, running the crawler is straightforward:

Bash

python main.py
The crawler will:

Create a project directory (e.g., MyAwesomeCrawler) if it doesn't exist.
Initialize or load the queue.txt (URLs to crawl) and crawled.txt (already crawled URLs).
Set up an SQLite database (scraped_data.db) within the project directory.
Start multi-threaded crawling from the homepage_url specified in config.yml.
Extract data, apply summarization (if enabled), and store it in the database.
Continue crawling new links found on pages until the queue is empty.
# 📂 Project Structure
main.py: The entry point of the crawler, responsible for loading configuration, initializing the spider, and managing the crawling process.
spider.py: Contains the core Spider class, handling page fetching, link gathering, data extraction, and storage. It interacts with the config for all operational settings.
link_finder.py: Parses HTML content to find links.
summerize.py: Provides AI summarization capabilities using the Google Gemini API, configured via config.yml and .env.
domain.py: Helper functions for domain-related operations (e.g., getting base domain from a URL).
general.py: General utility functions (e.g., file_to_set, set_to_file, create_project_dir).
config.yml: Your primary configuration file for crawler settings.
.env: Stores sensitive API keys.
requirements.txt: Lists all Python dependencies.
# 🤝 Contributing
Feel free to fork this repository, open issues, or submit pull requests. Any contributions to improve the crawler's functionality, efficiency, or robustness are welcome!
