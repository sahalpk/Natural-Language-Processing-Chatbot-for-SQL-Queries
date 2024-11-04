import os
import re
from fastapi import FastAPI
from pydantic import BaseModel
import sqlite3
import requests
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
# Initialize FastAPI app

app = FastAPI()
api_key = os.getenv("GROQ_API_KEY")  # This should fetch the key from the environment variable
if not api_key:
    raise ValueError("GROQ_API_KEY environment variable not set.")

# Initialize Groq client with the API key
client = Groq(api_key=api_key) 
# Allow cross-origin requests from your React app (localhost:3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Allow requests from your React app
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

class Query(BaseModel):
    question: str

# Function to connect to the SQLite database
def connect_db():
    conn = sqlite3.connect('database/chinook.db')
    return conn

# Translate natural language to SQL using Groq
def translate_with_groq(question):
    # Define the updated Chinook database schema
    chinook_schema = {
        "tables": [
            {"name": "albums", "Columns": ["AlbumId", "Title", "ArtistId"]},
            {"name": "artists", "Columns": ["ArtistId", "Name"]},
            {"name": "customers", "Columns": [
                "CustomerId", "FirstName", "LastName", "Company", "Address", "City", "State",
                "Country", "PostalCode", "Phone", "Fax", "Email", "SupportRepId"
            ]},
            {"name": "employees", "Columns": [
                "EmployeeId", "LastName", "FirstName", "Title", "ReportsTo", "BirthDate", 
                "HireDate", "Address", "City", "State", "Country", "PostalCode", "Phone", 
                "Fax", "Email"
            ]},
            {"name": "genres", "Columns": ["GenreId", "Name"]},
            {"name": "invoice_items", "Columns": ["InvoiceLineId", "InvoiceId", "TrackId", "UnitPrice", "Quantity"]},
            {"name": "invoices", "Columns": [
                "InvoiceId", "CustomerId", "InvoiceDate", "BillingAddress", "BillingCity", 
                "BillingState", "BillingCountry", "BillingPostalCode", "Total"
            ]},
            {"name": "media_types", "Columns": ["MediaTypeId", "Name"]},
            {"name": "playlist_track", "Columns": ["PlaylistId", "TrackId"]},
            {"name": "playlists", "Columns": ["PlaylistId", "Name"]},
            {"name": "tracks", "Columns": [
                "TrackId", "Name", "AlbumId", "MediaTypeId", "GenreId", "Composer", 
                "Milliseconds", "Bytes", "UnitPrice"
            ]}
        ],
        "indexes": [
            {"name": "IFK_AlbumArtistId", "Columns": ["ArtistId"]},
            {"name": "IFK_PlaylistTrackTrackId", "Columns": ["TrackId"]},
            {"name": "sqlite_autoindex_playlist_track_1", "Columns": ["PlaylistId", "TrackId"]},
            {"name": "IFK_EmployeeReportsTo", "Columns": ["ReportsTo"]},
            {"name": "IFK_InvoiceCustomerId", "Columns": ["CustomerId"]},
            {"name": "IFK_CustomerSupportRepId", "Columns": ["SupportRepId"]},
            {"name": "IFK_TrackAlbumId", "Columns": ["AlbumId"]},
            {"name": "IFK_TrackGenreId", "Columns": ["GenreId"]},
            {"name": "IFK_TrackMediaTypeId", "Columns": ["MediaTypeId"]},
            {"name": "IFK_InvoiceLineInvoiceId", "Columns": ["InvoiceId"]},
            {"name": "IFK_InvoiceLineTrackId", "Columns": ["TrackId"]}
        ],
        "sequences": [
            "genres", "media_types", "artists", "albums", "tracks", 
            "employees", "customers", "invoices", "invoice_items", "playlists"
        ],
        "triggers": [
            "genres", "media_types", "artists", "albums", "tracks", "employees", 
            "customers", "invoices", "invoice_items", "playlists"
        ],
        "data_types": [
            "INTEGER", "REAL", "NUMERIC", "TEXT", "BLOB"
        ]
    }


    # Make a request to the Groq API for chat completion
    payload = {
        "messages": [
            {
                "role": "system",
                "content": f"You are a SQL query generator. Given the following schema for the 'chinook' database and a natural language question, return the appropriate SQL query for an SQLite database:\n\n{chinook_schema}"
            },
            {
                "role": "user",
                "content": question
            }
        ],
        "model": "mixtral-8x7b-32768"
    }

    api_url = "https://api.groq.com/openai/v1/chat/completions"
    api_key = os.getenv('GROQ_API_KEY')
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        response = requests.post(api_url, json=payload, headers=headers)
        print("Groq API Response:", response.status_code, response.text)  # Log the response

        if response.status_code == 200:
            data = response.json()
            sql_query = data['choices'][0]['message']['content']

            # Extract only the SQL query from the Groq response, removing `sql` keyword and triple backticks
            sql_query_clean = re.search(r"```(?:sql)?\n(.*?)\n```", sql_query, re.DOTALL)
            if sql_query_clean:
                return sql_query_clean.group(1).strip()  # Return only the SQL part
            else:
                return {"error": "Failed to extract SQL query."}
        else:
            return {"error": f"Groq API Error: {response.status_code} {response.text}"}
    except Exception as e:
        return {"error": str(e)}

# Route to handle POST requests
@app.post("/ask")
def ask_question(query: Query):
    sql_query = translate_with_groq(query.question)

    # Log the generated SQL query for debugging
    print("Generated SQL Query:", sql_query)

    # Check if we received a valid SQL query
    if isinstance(sql_query, dict) and 'error' in sql_query:
        return {"error": sql_query['error']}
    elif not isinstance(sql_query, str):
        return {"error": "SQL query was not returned as a string."}

    conn = connect_db()
    cursor = conn.cursor()

    try:
        cursor.execute(sql_query)  # This should now be a valid SQL string
        result = cursor.fetchall()
    except sqlite3.OperationalError as e:
        return {"error": str(e)}
    finally:
        conn.close()

    return {"result": result}

