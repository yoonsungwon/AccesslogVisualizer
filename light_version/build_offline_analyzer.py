import os
import re
import urllib.request
import ssl

# Ignore potential SSL errors during download (for convenience in some envs)
ssl._create_default_https_context = ssl._create_unverified_context

SOURCE_FILE = 'analyzer.html'
OUTPUT_FILE = 'analyzer_offline.html'

def download_content(url):
    print(f"Downloading {url}...")
    try:
        req = urllib.request.Request(
            url, 
            data=None, 
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        )
        with urllib.request.urlopen(req) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return None

def main():
    if not os.path.exists(SOURCE_FILE):
        print(f"Error: {SOURCE_FILE} not found in current directory.")
        return

    print(f"Reading {SOURCE_FILE}...")
    with open(SOURCE_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # Regex to find script tags with CDN src
    # Matches <script src="..."></script>
    script_pattern = re.compile(r'<script src="(https?://[^"]+)"></script>')
    
    # Logic to replace
    def replace_script(match):
        url = match.group(1)
        js_content = download_content(url)
        if js_content:
            return f'<script>\n/* Embedded from {url} */\n{js_content}\n</script>'
        else:
            return match.group(0) # Keep original if download fails

    print("Embedding scripts...")
    new_content = script_pattern.sub(replace_script, content)

    # Handle Link tags if any (Fonts?)
    # Fonts are harder because they reference other files (woff2). 
    # For a truly offline 'light' tool, we might skip fonts or fallback to system fonts.
    # The current analyzer.html uses Google Fonts Inter.
    # We will replace the font link with a style block that defines system fonts as fallback
    # <link href="https://fonts.googleapis.com/css2?family=Inter:..." rel="stylesheet">
    
    font_pattern = re.compile(r'<link href="https://fonts.googleapis.com.*?" rel="stylesheet">')
    new_content = font_pattern.sub('', new_content) # Remove external font link

    print(f"Writing {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("Done! offline file created.")

if __name__ == '__main__':
    main()
