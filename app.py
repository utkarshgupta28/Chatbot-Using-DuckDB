import streamlit as st
import requests
import duckdb
import re
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
api_key = os.getenv("DEEPSEEK_API_KEY")

# Connect to DuckDB database
database_path = "E:/526-Data-Warehousing/Duckdb/imdb_cleaned.duckdb"
con = duckdb.connect(database_path)

# Extract SQL code block from LLM output
def extract_sql_code(response_text):
    matches = re.findall(r"```sql(.*?)```", response_text, re.DOTALL | re.IGNORECASE)
    return matches[0].strip() if matches else response_text.strip()

# Ask DeepSeek to generate SQL
def ask_deepseek(user_query):
    schema_prompt = """
You are a SQL assistant working with a DuckDB database containing:

Tables and Views:
- title_basics
- name_basics
- title_ratings
- title_crew
- title_principals
- title_episode
- title_akas
- movie_director_view
- movie_rating_view
- actor_known_titles_view

Guidelines:
- Match titles case-insensitively using LOWER().
- Always handle NULL values using COALESCE.
- Match directors, writers, knownForTitles fields using LIKE because they contain comma-separated IDs.
- Genres are stored as plain comma-separated text, not arrays. Use LIKE for genre matching. Do NOT use UNNEST or str_split.
- Use the table names exactly as they are defined in the database.
- Use the column names exactly as they are defined in the database.
- Write SQL queries using the SQL dialect and syntax supported by DuckDB.
- When filtering text fields like primaryTitle, originalTitle, genres, use LOWER(column_name) LIKE '%text%' instead of = to account for text variations.
"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "deepseek/deepseek-chat-v3-0324:free",
        "temperature": 0.0,
        "messages": [
            {"role": "user", "content": schema_prompt},
            {"role": "user", "content": user_query}
        ]
    }

    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)

    if response.status_code != 200:
        return None, f"API Error: {response.text}"

    sql_raw = response.json()["choices"][0]["message"]["content"]
    sql_clean = extract_sql_code(sql_raw)

    # Auto-correct common issues in generated SQL
    replacements = {
        "isOriginalTitle = 1": "COALESCE(isOriginalTitle, '') = '1'",
        "title_principals.job": "title_principals.category",
        "T1.titleId": "T1.tconst",
        "t2.title": "t2.primaryTitle",
        "md.directors": "md.director_name",
        "d.directors": "d.director_name",
        "SELECT UNNEST(str_split(LOWER(tb.genres), ','))": "LOWER(tb.genres)"
    }

    for wrong, correct in replacements.items():
        sql_clean = sql_clean.replace(wrong, correct)

    return sql_clean, None

# Initialize Streamlit session state
if "generated_sql" not in st.session_state:
    st.session_state["generated_sql"] = ""
if "user_query" not in st.session_state:
    st.session_state["user_query"] = ""

# Configure Streamlit page
st.set_page_config(page_title="IMDb Chatbot (DuckDB + DeepSeek)", layout="centered")
st.title("🎬 IMDb Chatbot (DuckDB + DeepSeek)")

# User input
user_query_input = st.text_input("Ask a question about IMDb data:")

# Button to generate SQL
if st.button("Generate SQL"):
    if not user_query_input:
        st.warning("Please enter a question first.")
    else:
        with st.spinner("Generating SQL..."):
            sql_generated, error = ask_deepseek(user_query_input)

            if error:
                st.error(error)
            elif sql_generated:
                st.session_state["generated_sql"] = sql_generated
                st.session_state["user_query"] = user_query_input

# Display generated SQL
if st.session_state["generated_sql"]:
    st.subheader("Generated SQL:")
    sql_to_run = st.text_area("Edit the SQL if needed:", value=st.session_state["generated_sql"], height=300)

    # Button to run SQL
    if st.button("Run SQL"):
        try:
            df_result = con.execute(sql_to_run).fetchdf()

            if df_result.empty:
                st.warning("No results found for this query.")
            else:
                st.success("Query executed successfully.")
                st.dataframe(df_result)

                # Option to download the results
                csv_data = df_result.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Results as CSV",
                    data=csv_data,
                    file_name="query_results.csv",
                    mime="text/csv"
                )
        except Exception as sql_error:
            st.error(f"SQL Execution Error:\n{sql_error}")
else:
    st.info("Enter a question and click 'Generate SQL' to begin.")