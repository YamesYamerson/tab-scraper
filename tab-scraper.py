import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import random
import re

def clean_tab_data(raw_text):
    # Remove common header/footer text and irrelevant sections
    clean_text = re.sub(r"Artist:.*?TabsUpdatesTop.*?\n", "", raw_text, flags=re.DOTALL)
    clean_text = re.sub(r"Comments.*?Privacy©.*", "", clean_text, flags=re.DOTALL)
    clean_text = re.sub(r"Email:.*?\n", "", clean_text, flags=re.MULTILINE)
    clean_text = re.sub(r"\[ Tab from:.*?\]", "", clean_text)
    clean_text = re.sub(r"Guide to Reading.*", "", clean_text)

    # Extract structured tab/chord data using a regular expression
    pattern = re.compile(r"\[(Intro|Verse|Chorus|Bridge|Outro|INTERLUDE)\](.*?)\[(?=(Intro|Verse|Chorus|Bridge|Outro|INTERLUDE)|$)", re.DOTALL)
    sections = pattern.findall(clean_text)
    
    # Dictionary to store the structured data
    tab_data = {}

    for section in sections:
        title, content, _ = section
        # Clean up each section content
        content = re.sub(r"(\r\n|\r|\n)+", '\n', content.strip())  # Normalize new lines
        content = re.sub(r"^\s+", '', content, flags=re.MULTILINE)  # Trim leading whitespace
        tab_data[title.strip()] = content

    return tab_data

# Example usage with a string from your data
raw_text = """Pearl Jam - Catholic Boy Chords & Tabs ... [Outro]E-------------------------|B-------------------------|"""
cleaned_data = clean_tab_data(raw_text)

# Print structured data
for section, content in cleaned_data.items():
    print(f"{section}:\n{content}\n")


# Set up the database connection and create a table for storing guitar tabs
conn = sqlite3.connect('guitartabs.db')
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS tabs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artist TEXT,
    title TEXT,
    url TEXT,
    content TEXT
)
''')
conn.commit()

# Function to make requests with a browser-like user-agent
def make_request(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
    return requests.get(url, headers=headers)

def fetch_tabs():
    base_url = 'https://www.guitartabs.cc'
    response = make_request(base_url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        # Looking for links that are likely to contain guitar tabs
        links = soup.find_all('a', href=True)
        for link in links:
            href = link['href']
            if '/tabs/' in href and href.endswith('.html'):
                full_url = base_url + href
                try:
                    # Introduce random delay
                    time.sleep(random.uniform(1, 3))
                    # Fetch tab detail page
                    tab_response = make_request(full_url)
                    tab_soup = BeautifulSoup(tab_response.text, 'html.parser')
                    # Extract tab content
                    tab_content = ''.join(text for text in tab_soup.stripped_strings if "Return to the" not in text)
                    # Simple extraction for artist and title from URL
                    parts = href.split('/')
                    artist = parts[2].replace('_', ' ').title()
                    title = parts[3].replace('_', ' ').replace('.html', '').title().replace(' Crd', '').replace(' Tab', '')
                    # Save the tab information into the database
                    cursor.execute('INSERT INTO tabs (artist, title, url, content) VALUES (?, ?, ?, ?)',
                                   (artist, title, full_url, tab_content))
                    conn.commit()
                    print(f"Processed tab: {artist} - {title}")
                except requests.exceptions.RequestException as e:
                    print(f"Failed to process {full_url}: {str(e)}")
            else:
                print(f"Skipping non-tab link {href}")

# Start the scraping process
fetch_tabs()

# Close the database connection when done
conn.close()
