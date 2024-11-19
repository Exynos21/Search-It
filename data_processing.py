import os
import re
import gspread
import time
from dotenv import load_dotenv
from serpapi import GoogleSearch
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from groq import Groq
import spacy

# Load environment variables from the .env file
load_dotenv()

# Constants
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SERP_API_KEY = os.getenv("SERPAPI_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GOOGLE_SHEETS_CREDENTIALS_PATH = os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH")

# Load the pre-trained SpaCy model for NER
nlp = spacy.load("en_core_web_sm")

# Retry logic
MAX_RETRIES = 3
RETRY_DELAY = 2


def authenticate_google():
    """
    Authenticate with Google API using OAuth2 and return credentials.

    Returns:
        google.oauth2.credentials.Credentials: Valid credentials object.
    """
    credentials = None
    if os.path.exists("token.json"):
        credentials = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                GOOGLE_SHEETS_CREDENTIALS_PATH, SCOPES
            )
            credentials = flow.run_local_server(port=0)

        # Save the token for future use
        with open("token.json", "w") as token_file:
            token_file.write(credentials.to_json())

    return credentials


def connect_to_google_sheet(sheet_url):
    """
    Connect to a Google Sheet using its URL.

    Args:
        sheet_url (str): The full Google Sheet URL.

    Returns:
        tuple: A connected Google Sheets service and the sheet ID.
    """
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", sheet_url)
    if not match:
        raise ValueError("Invalid Google Sheet URL. Could not extract spreadsheet ID.")

    sheet_id = match.group(1)

    try:
        credentials = authenticate_google()
        service = build("sheets", "v4", credentials=credentials)
        return service, sheet_id
    except Exception as e:
        raise ValueError(f"Error connecting to Google Sheets: {e}")


def search_entity_info(entity):
    """
    Perform a broad web search for the given entity and retrieve top 10 results.

    Args:
        entity (str): The entity to search for.

    Returns:
        list: A list of top search results, each containing title, URL, and snippet.
    """
    search = GoogleSearch({
        "q": entity,  # Broad search for the entity
        "api_key": SERP_API_KEY,
        "num": 10,  # Fetch top 10 results
        "hl": "en",  # Language
        "gl": "us",  # Target country
        "filter": "1",  # Exclude duplicate results
    })

    for attempt in range(MAX_RETRIES):
        try:
            results = search.get_dict()
            # //print(f"Search results for {entity}: {results}")
            if "organic_results" in results and results["organic_results"]:
                return [
                    {
                        "title": result.get("title", "N/A"),
                        "url": result.get("link", "N/A"),
                        "snippet": result.get("snippet", "N/A"),
                    }
                    for result in results["organic_results"]
                ]
            else:
                return []
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (2 ** attempt))
            else:
                raise Exception(f"Error performing search: {e}")

    return []  # Return an empty list if no results


def generate_query(entity, query_template):
    """
    Generate a query by replacing placeholders in the query template with the entity.

    Args:
        entity (str): The entity being processed.
        query_template (str): The user-defined query template.

    Returns:
        str: The generated query.
    """
    return query_template.replace("{entity}", entity)


def extract_information_with_groq(entity, search_results, query_template, query_type):
    """
    Use Groq to extract specific information based on user-defined query, search results, and query type.

    Args:
        entity (str): The entity being processed (e.g., a company or person name).
        search_results (list): The web search results containing titles, URLs, and snippets.
        query_template (str): The user-defined query template.
        query_type (str): The query classification type (e.g., Age Extraction).

    Returns:
        str: Extracted information or "Data not found" if unsuccessful.
    """
    client = Groq(api_key=GROQ_API_KEY)
    
    # Generate query dynamically
    query = query_template.replace("{entity}", entity)
    
    # Aggregate search results into a context string
    search_context = "\n\n".join(
        f"Title: {result['title']}\nURL: {result['url']}\nSnippet: {result['snippet']}"
        for result in search_results
    )

    # Refined prompt
    prompt = f"""
    Task: Extract the most relevant information for the following query based on the search results.

    Query: "{query}"
    Entity: {entity}
    Query Type: {query_type}

    Search Results:
    {search_context}

    Instructions:
    - If you find the exact answer, provide it directly in one word.
    - If relevant information is partially available, summarize the context.
    - If no relevant information is available, return: "Data not found."
    - Ensure the response is concise and accurate.
    """

    for attempt in range(MAX_RETRIES):
        try:
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama3-8b-8192",  # Example model for detailed extraction
            )
            return chat_completion.choices[0].message.content.strip()
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (2 ** attempt))
            else:
                raise Exception(f"Error calling Groq API: {e}")




def perform_ner(text):
    """
    Perform Named Entity Recognition (NER) on the given text to extract entities like dates, people, etc.

    Args:
        text (str): The text to perform NER on.

    Returns:
        dict: Extracted entities as key-value pairs.
    """
    doc = nlp(text)
    entities = {}
    for ent in doc.ents:
        entities[ent.label_] = ent.text
    return entities


def classify_query(query):
    """
    Classify the query type based on its structure (e.g., extracting emails, addresses, etc.).

    Args:
        query (str): The query template.

    Returns:
        str: The classification of the query type (e.g., "email extraction").
    """
    # Convert to lowercase to handle case insensitivity
    query_lower = query.lower()

    # Check for specific keywords to classify the query
    if "net worth" in query_lower:
        return "Net Worth"
    elif "age" in query_lower or "born" in query_lower:
        return "Age"
    elif "career" in query_lower or "biography" in query_lower:
        return "Biography"
    elif "parents" in query_lower or "family" in query_lower:
        return "Family Information"
    elif "job" in query_lower or "career" in query_lower:
        return "Career"
    elif "education" in query_lower or "school" in query_lower:
        return "Education"
    elif "married" in query_lower or "spouse" in query_lower:
        return "Personal Life"
    elif "award" in query_lower or "achievement" in query_lower:
        return "Awards & Achievements"
    elif "history" in query_lower or "background" in query_lower:
        return "Company Info"
    elif "product" in query_lower or "service" in query_lower:
        return "Product Info"
    elif "news" in query_lower or "latest" in query_lower:
        return "News"
    elif "social media" in query_lower or "twitter" in query_lower or "instagram" in query_lower:
        return "Social Media"
    elif "charity" in query_lower or "philanthropy" in query_lower:
        return "Philanthropy"
    elif "property" in query_lower or "real estate" in query_lower:
        return "Real Estate"
    elif "health" in query_lower or "condition" in query_lower:
        return "Health"
    elif "event" in query_lower or "conference" in query_lower:
        return "Events"
    elif "fruit" in query_lower or "vegetable" in query_lower:
        return "Fruit"
    else:
        return "Miscellaneous"

def preprocess_search_results(results):
    """
    Preprocess the search results to clean and prepare them for extraction.

    Args:
        results (list): A list of search results, where each result is a dictionary with keys like 'title', 'snippet', etc.

    Returns:
        list: A list of cleaned search results.
    """
    if not results or not isinstance(results, list):
        return []

    cleaned_results = []
    for result in results:
        if isinstance(result, dict):
            cleaned_result = {
                "title": result.get("title", "").strip(),
                "url": result.get("url", "").strip(),
                "snippet": result.get("snippet", "").strip(),
            }
            cleaned_results.append(cleaned_result)
    return cleaned_results
