from urllib.request import urlopen
from link_finder import LinkFinder
from domain import *
from general import *
from bs4 import BeautifulSoup
from config import EXCLUDE_TAGS, EXCLUDE_CLASSES, Summery_Mode
from summerize import generate_summary
import json

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
            print(str(e))
            return set()
        return finder.page_links()
    
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

            # save to a .json file, instead of .txt file.
            data_entry = {
            "url": page_url,
            "title": title,
            "text": text,
            }

            if Summery_Mode:
                data_entry["summary"] = generate_summary(text)

            json_file_path = Spider.project_name + '/data.json'

            try:
                with open(json_file_path, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    if not isinstance(existing_data, list): # Ensure it's a list for appending
                        existing_data = [existing_data] # Convert if it's a single object
            except (FileNotFoundError, json.JSONDecodeError):
                existing_data = [] # Start with an empty list if file doesn't exist or is invalid

            existing_data.append(data_entry)

            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=4)

        except Exception as e:
            print(f"Error extracting data from {page_url}: {str(e)}")

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
