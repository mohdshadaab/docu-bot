import requests
import os
from lxml import html
from bs4 import BeautifulSoup

# The FastAPI sitemap URL
import re

# Function to clean text and remove the feedback section
def clean_scraped_content(content):
    # Remove HTML/XML tags
    content = re.sub(r'<[^>]*>', '', content)

    # Remove the feedback section
    feedback_text = (
        r"Feedback\s+You're encouraged to help improve the quality of this guide.\s+"
        r"Please contribute if you see any typos or factual errors.*?on the official Ruby on Rails Forum\."
    )
    content = re.sub(feedback_text, '', content, flags=re.DOTALL)

    return content

sitemap_url = ""
with open("ror-sitemap.xml", "r") as f:
    sitemap_url = f.read()

# Create a folder to store the documentation
output_folder = "RoR-Docs"
os.makedirs(output_folder, exist_ok=True)

soup = BeautifulSoup(sitemap_url, 'xml')
urls = soup.find_all('loc')

    # Loop through each URL in the sitemap
for url in urls:
        page_url = url.text
        print(f"Scraping {page_url}...")

        try:
            # Request the content of the page
            page_response = requests.get(page_url)

            if page_response.status_code == 200:
                # Parse the page content with lxml and HTML parser
                tree = html.fromstring(page_response.content)

                # Use XPath to target the specific element (the article content)
                article_content = tree.xpath('/html/body/main/div/div')
                article_content_2 = tree.xpath('/html/body/div[5]/div/div')

                # Get the page title to use as the filename
                page_title = tree.xpath('//title/text()')
                if page_title:
                    # Clean the title to make it filename-friendly
                    page_title = page_title[0].strip().replace(' ', '_').replace('/', '_').replace('\\', '_')
                else:
                    page_title = "untitled_page"

                # Ensure we have content to write
                if article_content:
                    # Extract the text from the article section
                    content_text = article_content[0].text_content()

                    # Create a file for each page
                    file_path = os.path.join(output_folder, f"{page_title}.txt")
                    with open(file_path, 'w', encoding='utf-8') as file:
                        file.write(f"### Content from {page_url} ###\n")
                        file.write(clean_scraped_content(content_text))

                    print(f"Successfully scraped {page_url} and saved as {file_path}")
                elif article_content_2:
                    # Extract the text from the article section
                    content_text = article_content_2[0].text_content()

                    # Create a file for each page
                    file_path = os.path.join(output_folder, f"{page_title}.txt")
                    with open(file_path, 'w', encoding='utf-8') as file:
                        file.write(f"### Content from {page_url} ###\n")
                        file.write(clean_scraped_content(content_text))

                    print(f"Successfully scraped {page_url} and saved as {file_path}")
                else:
                    print(f"No content found at specified XPath in {page_url}")

            else:
                print(f"Failed to retrieve {page_url}")

        except Exception as e:
            print(f"Error occurred while scraping {page_url}: {e}")

else:
    print("Failed to fetch the sitemap.")
