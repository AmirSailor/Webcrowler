from urllib.request import urlopen
from link_finder import LinkFinder
from domain import *
from general import *
from bs4 import BeautifulSoup
from config import EXCLUDE_TAGS, EXCLUDE_CLASSES, Summery_Mode
from summerize import generate_summary
import json
from datetime import datetime
import re # Make sure 're' is imported for regex operations
import os # Make sure 'os' is imported for path operations
import traceback # Make sure 'traceback' is imported for detailed error logging

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
    # print(f"Could not parse date string: '{date_string}'") # Uncomment for debugging unparsed dates
    return None

class Spider:

    project_name = ''
    base_url = ''
    domain_name = ''
    queue_file = ''
    crawled_file = ''
    queue = set()
    crawled = set()

    def __init__(self, project_name, base_url, domain_name):
        Spider.project_name = project_name
        Spider.base_url = base_url
        Spider.domain_name = domain_name
        Spider.queue_file = Spider.project_name + '/queue.txt'
        Spider.crawled_file = Spider.project_name + '/crawled.txt'
        self.boot()
        self.crawl_page('First spider', Spider.base_url)

    # Creates directory and files for project on first run and starts the spider
    @staticmethod
    def boot():
        create_project_dir(Spider.project_name)
        create_data_files(Spider.project_name, Spider.base_url)
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
            response = urlopen(page_url)
            if 'text/html' in response.getheader('Content-Type'):
                html_bytes = response.read()
                html_string = html_bytes.decode("utf-8")
            finder = LinkFinder(Spider.base_url, page_url)
            finder.feed(html_string)
            Spider.extract_and_store_data(page_url, html_string)

        except Exception as e:
            print(f"Error gathering links from {page_url}: {str(e)}")
            traceback.print_exc() # Print full traceback for debugging
            return set()
        return finder.page_links()

    # --- Corrected extract_and_store_data method ---
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

            # Strategy 1: Look for <time> tags (most reliable if present)
            time_tag = soup.find('time')
            if time_tag:
                date_str = time_tag.get('datetime')
                if date_str:
                    post_date = date_str
                else:
                    post_date = time_tag.get_text(strip=True)

            # Strategy 2: Look for specific classes/IDs (customize these heavily)
            if not post_date:
                date_elements = soup.find_all(class_=['date', 'post-date', 'published', 'entry-date', 'article-date'])
                for elem in date_elements:
                    found_date_text = elem.get_text(strip=True)
                    # Call the global helper function
                    parsed_dt = parse_date_string(found_date_text)
                    if parsed_dt:
                        post_date = parsed_dt.isoformat()
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
                        # Call the global helper function
                        parsed_dt = parse_date_string(date_str)
                        if parsed_dt:
                            post_date = parsed_dt.isoformat()
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
                        # Call the global helper function
                        parsed_dt = parse_date_string(found_date_text)
                        if parsed_dt:
                            post_date = parsed_dt.isoformat()
                            break

            # --- End Date Extraction Logic ---

            data_entry = {
                "url": page_url,
                "title": title,
                "text": text,
                "date": post_date if post_date else "NO Date"
            }

            if Summery_Mode:
                data_entry["summary"] = generate_summary(text)

            project_dir = Spider.project_name
            if not os.path.exists(project_dir):
                os.makedirs(project_dir)

            json_file_path = os.path.join(project_dir, 'data.json')

            try:
                with open(json_file_path, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    if not isinstance(existing_data, list):
                        existing_data = [existing_data]
            except (FileNotFoundError, json.JSONDecodeError):
                existing_data = []

            existing_data.append(data_entry)

            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=4)

        except Exception as e:
            print(f"Error extracting or storing data from {page_url}: {str(e)}")
            traceback.print_exc()
            return None

    # Saves queue data to project files
    @staticmethod
    def add_links_to_queue(links):
        for url in links:
            if (url in Spider.queue) or (url in Spider.crawled):
                continue
            if Spider.domain_name != get_domain_name(url):
                continue
            Spider.queue.add(url)

    @staticmethod
    def update_files():
        set_to_file(Spider.queue, Spider.queue_file)
        set_to_file(Spider.crawled, Spider.crawled_file)
