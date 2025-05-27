import threading
from queue import Queue
from spider import spider
from domain import *
from General import *


Project_name = input('Please Write a Name for Your Project: ')
Home_page = input('Please insert the home page URL (e.g. http://example.com/) ')
Domain_name = get_domain(Home_page)
Queue_file = Project_name + '/queue.txt'
Crawled_file = Project_name = Project_name + '/crawled.txt'
Number_of_threads = input('Enter Number of Threads you can handle: ')

queue = Queue()
spider(Project_name, Home_page, Domain_name)