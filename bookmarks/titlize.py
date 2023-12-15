import re
import subprocess
import sys
import time

def get_title(url):
    url = url.encode("utf-8")
    title = None
    try:
        result = subprocess.run(['curl', '-s', '-L', url], stdout=subprocess.PIPE)
        title_result = subprocess.run(['xq', '-q', 'head title'], input=result.stdout, stdout=subprocess.PIPE)
        title = title_result.stdout.strip().decode("utf-8").replace("\r", "").replace("\n", "")
    except subprocess.CalledProcessError:
        return None

    # Strip out extra stuff we don't want.
    # print('before', title)
    title = re.sub(r'GitHub - [^\:]*: ', '', title)
    # print('after', title)
    title = re.sub(r'\s\s*', ' ', title)
    return title

def update_markdown_file(file_path, url, title):
    with open(file_path, 'r') as file:
        content = file.read()
    content = content.replace(url, f"{url} - {title}")
    with open(file_path, 'w') as file:
        file.write(content)

def main(mod_file):
    with open(mod_file, 'r') as file:
        lines = file.readlines()

    url_pattern = re.compile(r'^\s*-  *(http[^\s]*)\s*\n?$')
    urls = [m.group(1) for line in lines if ((m := url_pattern.match(line)) is not None and 'en.wikipedia.' not in line and 'reddit.com' not in line)]

    for url in urls:
        grabbed_title = get_title(url)
        if grabbed_title:
            print(f"{url} - {grabbed_title}")
            update_markdown_file(mod_file, url, grabbed_title)
        else:
            print(f"FAILED for {url}")
        time.sleep(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 script.py <markdown_file>")
        sys.exit(1)
    MOD_FILE = sys.argv[1]
    main(MOD_FILE)
