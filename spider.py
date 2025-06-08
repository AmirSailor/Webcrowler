from urllib.request import urlopen, Request # Make sure Request is imported
from urllib.robotparser import RobotFileParser # New import 
from link_finder import LinkFinder
from User_agents import USER_AGENTS
from domain import *
from general import *
from bs4 import BeautifulSoup
from config import EXCLUDE_TAGS, EXCLUDE_CLASSES, Summery_Mode
from summerize import generate_summary
import json
from datetime import datetime
import re
import os
import traceback
import sqlite3
import random # For User-Agent rotation and delays
import time # For delays

# --- Helper function for date parsing (should be outside the class or a static method) ---
def parse_date_string(date_string):
    """
    Attempts to parse a date string into a datetime object.
    You'll likely need to expand this with more formats based on your data.
    """
    formats = [
        "%Y-%m-%dT%H:%M:%S%z", # ISO 8601 with timezone (e.g., from <time datetime>)
        "%Y-%m-%d",          # YYYY-MM-DD
        "%B %d, %Y",         # Month Day, Year (e.g., January 1, 2023)
        "%d %B %Y",         # Day Month Year (e.g., 1 January 2023)
        "%m/%d/%Y",          # MM/DD/YYYY
        "%d/%m/%Y",          # DD/MM/YYYY
        "%Y/%m/%d",          # YYYY/MM/DD
        "%b %d, %Y",         # Abbreviated Month Day, Year (e.g., Jan 1, 2023)
        "%A, %B %d, %Y",     # Weekday, Month Day, Year (e.g., Friday, June 7, 2025)
        "%B %d, %Y %H:%M:%S", # Month Day, Year HH:MM:SS (e.g., June 7, 2025 10:30:00)
        "%m/%d/%Y %H:%M:%S",  # MM/DD/YYYY HH:MM:SS
        # Add more formats as you encounter them on different websites
    ]
    for fmt in formats:
        try:
            # For formats with timezone, handle if it's not always present
            if '%z' in fmt and ('+' not in date_string and '-' not in date_string[-6:]):
                # If timezone is expected but not in string, try without it
                return datetime.strptime(date_string.strip(), fmt.replace('%z', ''))
            return datetime.strptime(date_string.strip(), fmt)
        except ValueError:
            continue
    return None

# --- New Helper Function for Database Operations ---
def create_database_table(project_name):
    db_file_path = os.path.join(project_name, f'{project_name}.db')
    conn = None
    try:
        conn = sqlite3.connect(db_file_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                title TEXT,
                text TEXT,
                date TEXT,
                date_strategy TEXT,
                summary TEXT
            )
        ''')
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error during table creation: {e}")
        traceback.print_exc()
    finally:
        if conn:
            conn.close()

def insert_page_data(project_name, data):
    db_file_path = os.path.join(project_name, f'{project_name}.db')
    conn = None
    try:
        conn = sqlite3.connect(db_file_path)
        c = conn.cursor()

        # Handle 'None' for summary if Summery_Mode is False
        summary_data = data.get('summary') if Summery_Mode else None

        c.execute('''
            INSERT OR IGNORE INTO pages (url, title, text, date, date_strategy, summary)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            data['url'],
            data['title'],
            data['text'],
            data['date'],
            data['date_strategy'],
            summary_data
        ))
        conn.commit()
    except sqlite3.Error as e:
        # Check if the error is due to a UNIQUE constraint violation (duplicate URL)
        if "UNIQUE constraint failed: pages.url" in str(e):
            # print(f"Skipping duplicate URL: {data['url']}") # Uncomment if you want to see this
            pass # Keep quiet for expected duplicates
        else:
            print(f"Database error during data insertion for {data['url']}: {e}")
            traceback.print_exc()
    finally:
        if conn:
            conn.close()


class Spider:

    project_name = ''
    base_url = ''
    domain_name = ''
    queue_file = ''
    crawled_file = ''
    queue = set()
    crawled = set()
    db_file = ''
    robot_parser = None # New class attribute for RobotFileParser

    def __init__(self, project_name, base_url, domain_name):
        Spider.project_name = project_name
        Spider.base_url = base_url
        Spider.domain_name = domain_name
        Spider.queue_file = Spider.project_name + '/queue.txt'
        Spider.crawled_file = Spider.project_name + '/crawled.txt' # Corrected this line as discussed
        Spider.db_file = os.path.join(Spider.project_name, f'{Spider.project_name}.db')
        self.boot()
        self.crawl_page('First spider', Spider.base_url)

    # Creates directory and files for project on first run and starts the spider
    @staticmethod
    def boot():
        create_project_dir(Spider.project_name)
        create_data_files(Spider.project_name, Spider.base_url)
        create_database_table(Spider.project_name)

        # Initialize RobotFileParser
        Spider.robot_parser = RobotFileParser()
        robots_url = get_domain_name(Spider.base_url) + '/robots.txt' # Construct robots.txt URL
        # Ensure it's a full URL with scheme (http/https)
        if not (robots_url.startswith('http://') or robots_url.startswith('https://')):
            robots_url = "http://" + robots_url # Default to http if missing
            # A more robust solution might try both http and https, or derive from base_url's scheme

        Spider.robot_parser.set_url(robots_url)
        try:
            # Need to open the robots.txt file with custom headers as well
            # to prevent it from blocking based on default user-agent
            req = Request(robots_url, headers={'User-Agent': random.choice(USER_AGENTS)})
            response = urlopen(req)
            Spider.robot_parser.parse(response.read().decode("utf-8").splitlines())
            print(f"Successfully loaded robots.txt from: {robots_url}")
        except Exception as e:
            print(f"Could not load or parse robots.txt from {robots_url}: {e}")
            # If robots.txt cannot be loaded, the parser will assume everything is allowed,
            # which might not be desired for strict adherence. You might want to
            # set a flag here or handle this differently based on your policy.
            Spider.robot_parser = None # Indicate that parser failed to load


        Spider.queue = file_to_set(Spider.queue_file)
        Spider.crawled = file_to_set(Spider.crawled_file)

    # Updates user display, fills queue and updates files
    @staticmethod
    def crawl_page(thread_name, page_url):
        if page_url not in Spider.crawled:
            print(thread_name + ' now crawling ' + page_url)
            print('Queue ' + str(len(Spider.queue)) + ' | Crawled  ' + str(len(Spider.crawled)))
            Spider.add_links_to_queue(Spider.gather_links(page_url))
            Spider.queue.remove(page_url)
            Spider.crawled.add(page_url)
            Spider.update_files()

    # Converts raw response data into readable information and checks for proper html formatting
    @staticmethod
    def gather_links(page_url):
        html_string = ''
        try:
            # Random delay before making the request
            time.sleep(random.uniform(1, 3)) # Wait between 1 and 3 seconds

            # Prepare headers to mimic a browser
            headers = {
                'User-Agent': random.choice(USER_AGENTS),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0',
            }

            # Create a Request object with the URL and headers
            req = Request(page_url, headers=headers)

            response = urlopen(req)

            if 'text/html' in response.getheader('Content-Type'):
                html_bytes = response.read()
                html_string = html_bytes.decode("utf-8")
            finder = LinkFinder(Spider.base_url, page_url)
            finder.feed(html_string)
            Spider.extract_and_store_data(page_url, html_string)

        except Exception as e:
            print(f"Error gathering links from {page_url}: {str(e)}")
            traceback.print_exc()
            return set()
        return finder.page_links()

    # --- Modified extract_and_store_data method for SQL storage ---
    @staticmethod
    def extract_and_store_data(page_url, html_string):
        try:
            soup = BeautifulSoup(html_string, 'html.parser')

            # Remove unwanted tags
            for tag in EXCLUDE_TAGS:
                for element in soup.find_all(tag):
                    element.decompose()

            # Remove elements by class name
            for class_name in EXCLUDE_CLASSES:
                for element in soup.find_all(class_=lambda x: x and class_name in x):
                    element.decompose()

            title = soup.title.string if soup.title else 'No Title'
            text = soup.get_text(separator=' ', strip=True)

            # --- Date Extraction Logic ---
            post_date = None
            strategy = "No Strategy" # Initialize strategy here

            # Strategy 1: Look for <time> tags (most reliable if present)
            time_tag = soup.find('time')
            if time_tag:
                date_str = time_tag.get('datetime')
                if date_str:
                    post_date = date_str
                else:
                    post_date = time_tag.get_text(strip=True)
                strategy = 1

            # Strategy 2: Look for specific classes/IDs (customize these heavily)
            if not post_date:
                date_elements = soup.find_all(class_=['date', 'post-date', 'published', 'entry-date', 'article-date'])
                for elem in date_elements:
                    found_date_text = elem.get_text(strip=True)
                    parsed_dt = parse_date_string(found_date_text)
                    if parsed_dt:
                        post_date = parsed_dt.isoformat()
                        strategy = 2
                        break

            # Strategy 3: Look in meta tags
            if not post_date:
                meta_date_tags = soup.find_all('meta', attrs={
                    'property': ['article:published_time', 'og:pubdate'],
                    'name': ['date', 'pubdate', 'DC.date.issued', 'last_updated']
                })
                for tag in meta_date_tags:
                    date_str = tag.get('content')
                    if date_str:
                        parsed_dt = parse_date_string(date_str)
                        if parsed_dt:
                            post_date = parsed_dt.isoformat()
                            strategy = 3
                            break

            # Strategy 4: Search for common date patterns within the main text (less reliable)
            if not post_date:
                date_patterns = [
                    r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}\b',
                    r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',
                    r'\b\d{4}-\d{2}-\d{2}\b',
                    r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b',
                    r'\b(?:Published|Posted|Last updated):\s*(\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4})\b'
                ]
                for pattern in date_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        found_date_text = match.group(1) if len(match.groups()) > 0 else match.group(0)
                        parsed_dt = parse_date_string(found_date_text)
                        if parsed_dt:
                            post_date = parsed_dt.isoformat()
                            strategy = 4
                            break

            # --- End Date Extraction Logic ---

            # Prepare data for SQL insertion
            data_to_store = {
                "url": page_url,
                "title": title,
                "text": text,
                "date": post_date if post_date else "NO Date",
                "date_strategy": str(strategy),
                "summary": generate_summary(text) if Summery_Mode else None
            }

            # --- Store data in SQLite ---
            insert_page_data(Spider.project_name, data_to_store)

        except Exception as e:
            print(f"Error extracting or storing data from {page_url}: {str(e)}")
            traceback.print_exc()
            return None

    # Saves queue data to project files
    @staticmethod
    def add_links_to_queue(links):
        for url in links:
            # Skip if already in queue or crawled
            if (url in Spider.queue) or (url in Spider.crawled):
                continue
            # Skip if not in the same domain
            if Spider.domain_name != get_domain_name(url):
                continue

            # --- NEW: robots.txt check ---
            if Spider.robot_parser: # Only check if parser was successfully loaded
                # Pick a random user-agent to test with robots.txt
                # This ensures the check is relevant to your crawling identity
                if not Spider.robot_parser.can_fetch(random.choice(USER_AGENTS), url):
                    # print(f"Skipping disallowed link by robots.txt: {url}") # Uncomment to see skipped links
                    continue # Skip if robots.txt disallows it
            else:
                # If robots.txt failed to load, you might want to log a warning
                pass 

            Spider.queue.add(url)

    @staticmethod
    def update_files():
        set_to_file(Spider.queue, Spider.queue_file)
        set_to_file(Spider.crawled, Spider.crawled_file)
