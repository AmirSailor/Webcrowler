from urllib.parse import urlparse

def get_domain(url):
    try:
        results = get_sub_domains(url).split('.')
        return results[-2] + '.' + results[-1]
    except:
        return ''

#get sub domains (main.example.com)
def get_sub_domains(url):
    try:
        return urlparse(url).netloc
    except:
        return ''