from html.parser import HTMLParser
from urllib import parse


class linkfinder(HTMLParser):

    def __init__(self, base_url, page_url, *, convert_charrefs = True):
        super().__init__(convert_charrefs=convert_charrefs)
        self.base_url= base_url
        self.page_url = page_url
        self.links = set()

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for (attribute, value) in attrs:
                if attribute == 'href':
                    url = parse.urljoin(self.base_url, value)
                    self.links.add(url)

    def page_links(self):
        return self.links


    def error(self, massage):
        pass