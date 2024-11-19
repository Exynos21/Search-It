import os
import pandas as pd
import re
import streamlit as st
import time
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import traceback
from data_processing import (
    connect_to_google_sheet,
    search_entity_info,
    extract_information_with_groq,
    classify_query,
    perform_ner,
    preprocess_search_results,  # Import the preprocessing function
)

# Load environment variables
load_dotenv()

# Constants for Google API and rate-limiting
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
RATE_LIMIT_DELAY = 2  # Delay in seconds between API calls
MAX_RETRIES = 3  # Maximum retries for API calls

def extract_sheet_id(url):
    match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    else:
        raise ValueError("Invalid Google Sheets URL. Could not extract Sheet ID.")


# Retry logic for API calls
def safe_api_call(api_function, *args, **kwargs):
    for attempt in range(MAX_RETRIES):
        try:
            response = api_function(*args, **kwargs)
            return response
        except Exception as e:
            st.error(f"Attempt {attempt + 1}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RATE_LIMIT_DELAY * (2 ** attempt))
            else:
                st.error("All retries failed.")
    return None


# Function to upload results to Google Sheets
def upload_to_google_sheet(dataframe, sheet_id, sheet_range="Sheet1!A1"):
    ###logs
    print("[INFO] 8")
    credentials = None
    if os.path.exists("token.json"):
        credentials = Credentials.from_authorized_user_file("token.json", SCOPES)
    ###logs
    print("[INFO] 9")
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH"), SCOPES
            )
            credentials = flow.run_local_server(port=0)
        ###logs
        print("[INFO] 10")
        
        with open("token.json", "w") as token:
            token.write(credentials.to_json())

    try:
        service = build("sheets", "v4", credentials=credentials)
        sheet = service.spreadsheets()
        ###logs
        print("[INFO] 11")
        # Convert dataframe to list of lists
        values = [list(dataframe.columns)] + dataframe.values.tolist()
        body = {"values": values}
        ###logs
        print("[INFO] 12")
        sheet.values().update(
            spreadsheetId=sheet_id,
            range=sheet_range,
            body=body,
            valueInputOption="RAW"
        ).execute()
        ###logs
        print("[INFO] 13")
        st.success(f"Data uploaded successfully to Google Sheet: {sheet_id}")
    except Exception as e:
        st.error(f"Error uploading to Google Sheets: {e}")

def safe_upload_to_google_sheet(dataframe, sheet_url):
    """
    Safely upload DataFrame to Google Sheet with comprehensive error handling
    """
    ###logs
    print("[INFO] 4")
    try:
        ###logs
        print("[INFO] 5")
        # Validate inputs
        if dataframe is None or dataframe.empty:
            st.error("No data available for upload. Please run extraction first.")
            return False

        if not sheet_url:
            st.error("Please provide a valid Google Sheet URL.")
            return False

        # Extract sheet ID
        sheet_id = extract_sheet_id(sheet_url)
        ###logs
        print("[INFO] 6")
        # Attempt upload
        upload_to_google_sheet(dataframe, sheet_id)
        ###logs
        print("[INFO] 7")
        st.success("Successfully uploaded to Google Sheet!")
        return True

    except Exception as e:
        st.error(f"Upload failed: {e}")
        st.error(traceback.format_exc())  # Print full traceback for debugging
        return False

def render_results_and_upload():
    """
    Render results and provide upload functionality with robust error handling
    """
    try:
        # # Ensure results exist in session state
        # if "results_df" not in st.session_state or st.session_state.results_df is None:
        #     st.warning("No results available. Please run the extraction process first.")
        #     return

        # Display results
        st.write("### Extracted Information")
        st.dataframe(st.session_state.results_df)

        # Download CSV option
        csv = st.session_state.results_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Results as CSV", 
            data=csv, 
            file_name='results.csv', 
            mime='text/csv'
        )

        # Google Sheets Upload Section
        st.write("### Google Sheets Upload")

        if "sheet_url" not in st.session_state:
            st.session_state.sheet_url = ""  # Initialize sheet_url in session state

        # Sheet URL input with a unique key
        st.session_state.sheet_url = st.text_input(
            "Enter Google Sheets URL", 
            value=st.session_state.sheet_url,
            key="sheet_url_input_unique"
        )
        ##Logs
        print("[INFO] 0")
        ##Upload button
        if st.button("Upload to Google Sheet", key="upload_button_unique"):
            ###logs
        #     print("[INFO] 1")
            if st.session_state.sheet_url:
                 # Call safe upload function
        #         ###logs
        #         print("[INFO] 2")
                success = safe_upload_to_google_sheet(
                    st.session_state.results_df, 
                    st.session_state.sheet_url
                )
        #         ###logs
        #         print("[INFO] 3")
                if success:
                    st.balloons()  # Celebration effect on successful upload
                else:
                    st.error("Please enter a valid Google Sheets URL.")
        # # Refactor the button separately
        # if st.button("Test Button"):
        #     st.write("<script>console.log('Test button clicked');</script>", unsafe_allow_html=True)

        #     print("[INFO] Test button clicked")  # This should print in the terminal
        #     st.text("Test button clicked")  # This should appear in the browser log

    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        st.error(traceback.format_exc())

# Streamlit app setup
st.title("AI Data Retrieval and Extraction Dashboard")

# Upload options
st.sidebar.title("Data Input Options")
data_source = st.sidebar.selectbox("Choose Data Source", ["Upload CSV", "Google Sheet"])
data = None

# Check if data is already stored in session state
if 'data' in st.session_state:
    data = st.session_state.data

if data_source == "Upload CSV":
    uploaded_file = st.sidebar.file_uploader("Upload a CSV file", type=["csv"])
    if uploaded_file:
        data = pd.read_csv(uploaded_file)
        st.success("CSV file uploaded successfully!")
        # Store in session state to retain it on reruns
        st.session_state.data = data
elif data_source == "Google Sheet":
    sheet_url = st.sidebar.text_input("Enter Google Sheet URL")
    if st.sidebar.button("Load Google Sheet"):
        try:
            # Connect to Google Sheet
            service, sheet_id = connect_to_google_sheet(sheet_url)
            sheet = service.spreadsheets()

            # Retrieve spreadsheet metadata to get sheet names
            metadata = sheet.get(spreadsheetId=sheet_id).execute()
            sheet_names = [sheet['properties']['title'] for sheet in metadata['sheets']]

            # Ask user to select a sheet from the available names
            sheet_name = st.sidebar.selectbox("Select a sheet", sheet_names)

            # Fetch data from the selected sheet
            result = sheet.values().get(spreadsheetId=sheet_id, range=sheet_name).execute()
            values = result.get("values", [])
            
            if not values:
                st.error(f"The selected sheet '{sheet_name}' is empty or no values found.")
            elif len(values) == 1:
                st.error(f"The sheet '{sheet_name}' has headers but no data rows.")
            else:
                # Convert values to DataFrame
                data = pd.DataFrame(values[1:], columns=values[0])
                st.success(f"Google Sheet '{sheet_name}' loaded successfully!")
                # st.write("### Data Preview")
                # st.dataframe(data.head())  # Preview the first few rows
                
                # Store the data in session state
                st.session_state.data = data

        except ValueError as ve:
            st.error(f"Invalid URL or value error: {ve}")
        except Exception as e:
            st.error(f"Error loading Google Sheet: {e}")


if data is not None:
    st.write("### Data Preview")
    st.dataframe(data.head())

    # Select column and query template
    primary_column = st.selectbox("Select the column for entity extraction:", data.columns)
    query_template = st.text_area(
        "Enter a query template. Use `{entity}` as a placeholder for column values.",
        value="Extract the email and address for {entity}",
    )

    # Buttons for processing
    if st.button("Run Search and Extract Information"):
        results = []

        with st.spinner("Processing entities..."):
            for entity in data[primary_column]:
                # Step 1: Use NER to identify entities (if needed for further queries)
                ner_results = perform_ner(entity)

                # Step 2: Classify the query type (e.g., extracting age, email, etc.)
                query_type = classify_query(query_template)

                # Perform web search with retries
                web_result = safe_api_call(search_entity_info, entity)

                if web_result:
                    # Preprocess search results
                    preprocessed_results = preprocess_search_results(web_result)

                    # Extract information using Groq
                    extracted_info = safe_api_call(
                        extract_information_with_groq, entity, preprocessed_results, query_template, query_type
                    )

                    results.append({
                        "Entity": entity,
                        "Extracted Information": extracted_info or "Failed to extract",
                        "Search Title": ", ".join([result.get("title", "") for result in preprocessed_results]),
                        "Search URL": ", ".join([result.get("url", "") for result in preprocessed_results]),
                        "Search Snippet": ", ".join([result.get("snippet", "") for result in preprocessed_results]),
                        "NER Results": ner_results,
                        "Query Type": query_type
                    })
                else:
                    results.append({
                        "Entity": entity,
                        "Extracted Information": "No search results found",
                        "Search Title": "",
                        "Search URL": "",
                        "Search Snippet": "",
                        "NER Results": ner_results,
                        "Query Type": query_type
                    })

                # Rate-limiting to avoid API blocking
                time.sleep(RATE_LIMIT_DELAY)
        results_columns = [
            "Entity", 
            "Extracted Information", 
            "Search Title", 
            "Search URL", 
            "Search Snippet", 
            "NER Results", 
            "Query Type"
        ]

        st.session_state.results_df = pd.DataFrame(results, columns=results_columns)

        # Call render and upload function
        render_results_and_upload()