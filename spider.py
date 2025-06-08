from urllib.request import urlopen, Request
from urllib.robotparser import RobotFileParser
from link_finder import LinkFinder
from domain import *
from general import *
from bs4 import BeautifulSoup
from summerize import generate_summary
from datetime import datetime
import re
import os
import traceback
import sqlite3
import random
import time
import sys # For error handling in robots.txt fallback


# --- Helper function for date parsing (no changes needed here) ---
def parse_date_string(date_string):
    """
    Attempts to parse a date string into a datetime object.
    """
    formats = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d",
        "%B %d, %Y",
        "%d %B %Y",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%b %d, %Y",
        "%A, %B %d, %Y",
        "%B %d, %Y %H:%M:%S",
        "%m/%d/%Y %H:%M:%S",
    ]
    for fmt in formats:
        try:
            if '%z' in fmt and ('+' not in date_string and '-' not in date_string[-6:]):
                return datetime.strptime(date_string.strip(), fmt.replace('%z', ''))
            return datetime.strptime(date_string.strip(), fmt)
        except ValueError:
            continue
    return None

# --- Updated Helper Functions for Database Operations ---
# Now takes database_filename from config
def create_database_table(project_name, database_filename):
    db_file_path = os.path.join(project_name, database_filename)
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

# Now takes database_filename and summary_mode_enabled from config
def insert_page_data(project_name, database_filename, data, summary_mode_enabled):
    db_file_path = os.path.join(project_name, database_filename)
    conn = None
    try:
        conn = sqlite3.connect(db_file_path)
        c = conn.cursor()

        # Handle 'None' for summary if summary_mode_enabled is False
        summary_data = data.get('summary') if summary_mode_enabled else None

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
        if "UNIQUE constraint failed: pages.url" in str(e):
            pass
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
    robot_parser = None
    config = {} # This will store the loaded config dictionary

    def __init__(self, project_name, base_url, domain_name, config):
        Spider.project_name = project_name
        Spider.base_url = base_url
        Spider.domain_name = domain_name
        Spider.queue_file = Spider.project_name + '/queue.txt'
        Spider.crawled_file = Spider.project_name + '/crawled.txt'
        # Get database_filename from config, with a fallback
        Spider.db_file = os.path.join(Spider.project_name, config.get('database_filename', f'{project_name}.db'))
        Spider.config = config # Store the entire config dictionary
        self.boot()
        self.crawl_page('First spider', Spider.base_url)

    @staticmethod
    def boot():
        create_project_dir(Spider.project_name)
        create_data_files(Spider.project_name, Spider.base_url)
        # Pass database_filename from config to the helper function
        create_database_table(Spider.project_name, Spider.config.get('database_filename', f'{Spider.project_name}.db'))

        Spider.robot_parser = RobotFileParser()
        robots_url = get_domain_name(Spider.base_url) + '/robots.txt'

        # Infer scheme from base_url or default to http
        if not (robots_url.startswith('http://') or robots_url.startswith('https://')):
            if Spider.base_url.startswith('https://'):
                robots_url = "https://" + get_domain_name(Spider.base_url) + '/robots.txt'
            else:
                robots_url = "http://" + get_domain_name(Spider.base_url) + '/robots.txt'

        Spider.robot_parser.set_url(robots_url)
        try:
            # Use USER_AGENTS from config for robots.txt request
            user_agents_list = Spider.config.get('user_agents', [])
            if not user_agents_list: # Fallback if user_agents are not defined in config
                print("Warning: 'user_agents' not found in config.yml. Using a default user-agent for robots.txt.")
                user_agents_list = ["Mozilla/5.0 (compatible; MyCrawler/1.0)"]

            req = Request(robots_url, headers={'User-Agent': random.choice(user_agents_list)})
            response = urlopen(req)
            Spider.robot_parser.parse(response.read().decode("utf-8").splitlines())
            print(f"Successfully loaded robots.txt from: {robots_url}")
        except Exception as e:
            print(f"Could not load or parse robots.txt from {robots_url}: {e}", file=sys.stderr) # Print to stderr
            # If robots.txt fails, the parser will assume everything is allowed by default.
            # You might want to log this heavily or stop if strict adherence is required.
            Spider.robot_parser = None # Indicate that parser failed to load


        Spider.queue = file_to_set(Spider.queue_file)
        Spider.crawled = file_to_set(Spider.crawled_file)

    @staticmethod
    def crawl_page(thread_name, page_url):
        if page_url not in Spider.crawled:
            print(thread_name + ' now crawling ' + page_url)
            print('Queue ' + str(len(Spider.queue)) + ' | Crawled  ' + str(len(Spider.crawled)))
            Spider.add_links_to_queue(Spider.gather_links(page_url))
            Spider.queue.remove(page_url)
            Spider.crawled.add(page_url)
            Spider.update_files()

    @staticmethod
    def gather_links(page_url):
        html_string = ''
        try:
            # Get min/max delay from config
            min_delay = Spider.config.get('min_delay_seconds', 1)
            max_delay = Spider.config.get('max_delay_seconds', 3)
            time.sleep(random.uniform(min_delay, max_delay))

            # Get USER_AGENTS list from config
            user_agents_list = Spider.config.get('user_agents', [])
            if not user_agents_list: # Fallback if user_agents are not defined in config
                print("Warning: 'user_agents' not found in config.yml for requests. Using a default.")
                user_agents_list = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"] # Default fallback

            headers = {
                'User-Agent': random.choice(user_agents_list), # Use agent from config
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0',
            }

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

    @staticmethod
    def extract_and_store_data(page_url, html_string):
        try:
            soup = BeautifulSoup(html_string, 'html.parser')

            # Get EXCLUDE_TAGS from config
            exclude_tags = Spider.config.get('exclude_tags', [])
            for tag in exclude_tags:
                for element in soup.find_all(tag):
                    element.decompose()

            # Get EXCLUDE_CLASSES from config
            exclude_classes = Spider.config.get('exclude_classes', [])
            for class_name in exclude_classes:
                # Use lambda for class_ attribute to handle multiple classes
                for element in soup.find_all(class_=lambda x: x and class_name in x.split()):
                    element.decompose()

            title = soup.title.string if soup.title else 'No Title'
            text = soup.get_text(separator=' ', strip=True)

            post_date = None
            strategy = "No Strategy"

            # --- Date Extraction Logic (remains unchanged) ---
            time_tag = soup.find('time')
            if time_tag:
                date_str = time_tag.get('datetime')
                if date_str:
                    post_date = date_str
                else:
                    post_date = time_tag.get_text(strip=True)
                strategy = 1

            if not post_date:
                date_elements = soup.find_all(class_=['date', 'post-date', 'published', 'entry-date', 'article-date'])
                for elem in date_elements:
                    found_date_text = elem.get_text(strip=True)
                    parsed_dt = parse_date_string(found_date_text)
                    if parsed_dt:
                        post_date = parsed_dt.isoformat()
                        strategy = 2
                        break

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
            # Get Summery_Mode (summary_mode) from config
            summary_mode_enabled = Spider.config.get('summary_mode', False)

            data_to_store = {
                "url": page_url,
                "title": title,
                "text": text,
                "date": post_date if post_date else "NO Date",
                "date_strategy": str(strategy),
                "summary": generate_summary(text) if summary_mode_enabled else None
            }

            # Pass database_filename and summary_mode_enabled to insert_page_data
            insert_page_data(
                Spider.project_name,
                Spider.config.get('database_filename', f'{Spider.project_name}.db'),
                data_to_store,
                summary_mode_enabled
            )

        except Exception as e:
            print(f"Error extracting or storing data from {page_url}: {str(e)}")
            traceback.print_exc()
            return None

    @staticmethod
    def add_links_to_queue(links):
        for url in links:
            if (url in Spider.queue) or (url in Spider.crawled):
                continue
            if Spider.domain_name != get_domain_name(url):
                continue

            if Spider.robot_parser:
                # Get USER_AGENTS from config for robots.txt can_fetch check
                user_agents_list = Spider.config.get('user_agents', [])
                if not user_agents_list: # Fallback if user_agents are not defined in config
                    user_agents_list = ["Mozilla/5.0 (compatible; MyCrawler/1.0)"] # Default fallback

                if not Spider.robot_parser.can_fetch(random.choice(user_agents_list), url):
                    continue

            Spider.queue.add(url)

    @staticmethod
    def update_files():
        set_to_file(Spider.queue, Spider.queue_file)
        set_to_file(Spider.crawled, Spider.crawled_file)
