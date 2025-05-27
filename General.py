import os

def create_proj_dir(directory):
    if not os.path.exists(directory):
        print('createing project ' + directory)
        os.makedirs(directory)

#build queue and crawled files if it's not already created
def creat_data_file(project_name, base_url):
    queue = project_name + '/queue.txt'
    crawled = project_name + '/crawled.txt'
    if not os.path.isfile(queue):
        write_file(queue, base_url)
    if not os.path.isfile(crawled):
        write_file(crawled, '')

# creat new file
def write_file(path, data):
    f = open(path, 'w')
    f.write(data)
    f.close()

#add data into existing one
def append_into_file(path, data):
    with open(path, 'a')as file:
        file.write(data + '\n')

#delete
def delete_file_contents(path):
    with open(path, 'w'):
        pass

#read file and convert each lin to set
def file_to_set(file_name):
    results = set()
    with open(file_name, 'rt') as f:
        for line in f:
            results.add(line.replace('\n', ''))
    return results

#iterate through a set (set to file)
def set_to_file(links, file):
    delete_file_contents(file)
    for link in sorted(links):
        append_into_file(file, link)