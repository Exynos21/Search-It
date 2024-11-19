
# Search-It

This project is a user-friendly dashboard that leverages AI and web scraping to extract targeted information from online sources. Users can upload a dataset (CSV/Google Sheets), define custom search queries, and retrieve structured information for each entity.
### Key Features:
- **Automated Web Searches:** Use APIs like SerpAPI for efficient data retrieval.
- **AI-Powered Information Extraction:** Employ language models to parse and extract relevant data.
- **Batch Processing:** Handle large datasets with retry logic and detailed error reporting.
- **Google Sheets Integration:** Streamline data import/export through seamless Sheets connectivity.
- **Data Preprocessing**: The app automatically preprocesses the search results, improving the accuracy and relevance of extracted data.
- **Error Handling**: Detailed error messages and logs help diagnose issues with API calls or data input.
- **User-Friendly Dashboard:** Simplified interface for uploading datasets, configuring queries, and downloading results.


## Setup Instructions
### Prerequisites
Ensure you have the following installed on your system:
- Python 3.8 or later
- pip (Python package manager)
- Virtual environment tools (venv or virtualenv)

Follow these steps to set up and run the project locally:

1. Clone the repository:
   ```bash
   git clone https://github.com/Exynos21/Search-It.git
   cd Search-It
   ```
2. Create and activate a virtual environment:
    ```bash
    python -m venv myenv
    source myenv/bin/activate    # For macOS/Linux
    myenv\Scripts\activate       # For Windows
    ```

3. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4. Add your API keys and environment variables:
- Rename `.env.example` to `.env` and add your API keys:
```bash
SERP_API_KEY=your_serpapi_key
GROQ_API_KEY=your_groq_api_key
```
- Rename `credentials.json.example` to `credentials.json` and update it with your Google Sheets API credentials.

5. Run the Application:
    ```bash
    streamlit run app.py
    ```
6. Open your browser and go to the URL provided by Streamlit, usually `http://localhost:8501`, to access the dashboard.

## Usage Guide

1. **Upload Data** :- Upload a CSV file or connect to a Google Sheet to load your data.
2. **Define Search Queries** :- 
- Choose the primary column from your data that contains the entities you want to search for.
- Define the search pattern for each entity by inputting a custom query in the provided search fields.
- Example search query: *Find the latest product reviews for `{entity}`*
3. **View and Download Results** :-
- Processed data will be displayed in the dashboard.
- Download the final dataset as a CSV for further analysis.
- Alternatively, you can upload the processed data directly to your Google Sheet by selecting the "Upload to Google Sheets" option in the dashboard.
## API Keys and Environment Variables

Make sure to set up the following API keys and environment variables for the app to function correctly:

- **SERP_API_KEY**: This is required to connect to SerpAPI for web search queries.
- **GROQ_API_KEY**: Used for processing data with Groq.
- **Google Sheets API Credentials**: The `credentials.json` file, which contains your Google Sheets API credentials.

Ensure that you have the **.env** and **credentials.json** files set up correctly by renaming `.env.example` and `credentials.json.example` to `.env` and `credentials.json` respectively, and filling in your keys.

## Demo Video

Watch a quick walkthrough of the project [here](https://www.loom.com/share/4d96506ab32e4df6b20816233587b118?sid=204606d8-b89c-459f-b757-b301cfd83b5d).


