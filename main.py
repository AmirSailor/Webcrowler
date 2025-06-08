import threading
from queue import Queue
import yaml # Import the yaml library


from spider import Spider
from domain import * # Assuming get_domain_name is here
from general import * # Assuming file_to_set is here

# --- Configuration Loading ---
CONFIG_FILE = 'config.yml'

if not os.path.exists(CONFIG_FILE):
    print(f"Error: Configuration file '{CONFIG_FILE}' not found.")
    print("Please create a config.yml file in the same directory as main.py.")
    exit(1)

try:
    with open(CONFIG_FILE, 'r') as f:
        config = yaml.safe_load(f)
except yaml.YAMLError as e:
    print(f"Error parsing configuration file '{CONFIG_FILE}': {e}")
    exit(1)
except Exception as e:
    print(f"An unexpected error occurred while reading '{CONFIG_FILE}': {e}")
    exit(1)

# Use .get() with a default for robustness, especially for optional settings
PROJECT_NAME = config.get('project_name')
HOMEPAGE = config.get('homepage_url')
DOMAIN_NAME = get_domain_name(HOMEPAGE) if HOMEPAGE else None # Ensure HOMEPAGE exists
NUMBER_OF_THREADS = config.get('number_of_threads', 8) # Default to 8 threads if not specified in config

# Validate essential config values
if not all([PROJECT_NAME, HOMEPAGE, DOMAIN_NAME]):
    print("Error: Missing essential configuration values (project_name, homepage_url, domain_name) in config.yml.")
    exit(1)

# File paths derived from project name
QUEUE_FILE = os.path.join(PROJECT_NAME, 'queue.txt')
CRAWLED_FILE = os.path.join(PROJECT_NAME, 'crawled.txt')

# --- Crawler Initialization ---
queue = Queue()
# Pass the full config dictionary to the Spider
Spider(PROJECT_NAME, HOMEPAGE, DOMAIN_NAME, config)

# --- Worker Functions (remain largely the same) ---
def create_workers():
    """Creates worker threads that will process URLs from the queue."""
    for _ in range(NUMBER_OF_THREADS):
        t = threading.Thread(target=work)
        t.daemon = True  # Allows the main program to exit even if threads are running
        t.start()

def work():
    """Worker function: gets a URL from the queue, crawls it, and marks the job as done."""
    while True:
        url = queue.get()
        Spider.crawl_page(threading.current_thread().name, url)
        queue.task_done()

def create_jobs():
    """Puts links from the queue file into the thread queue."""
    for link in file_to_set(QUEUE_FILE):
        queue.put(link)
    queue.join() # Blocks until all items in the queue have been processed
    crawl() # After jobs are done, check if there's more to crawl

def crawl():
    """Checks the queue file and initiates new jobs if there are links."""
    queued_links = file_to_set(QUEUE_FILE)
    if len(queued_links) > 0:
        print(f"{len(queued_links)} links in the queue. Starting jobs...")
        create_jobs()
    else:
        print("Queue is empty. Crawling finished or nothing to crawl.")


# --- Start the Crawler ---
print(f"Starting crawler for project: {PROJECT_NAME}")
create_workers()
crawl()
print("Main program finished.")
