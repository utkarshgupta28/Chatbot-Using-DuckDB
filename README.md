# Chatbot Using DuckDB

This project is a chatbot application that allows users to interact with a structured IMDb dataset using natural language queries. The chatbot translates the queries to SQL, executes them using DuckDB, and displays the results via a Streamlit interface.

## Features

- Translate natural language questions into SQL
- Execute queries using DuckDB (embedded, no server required)
- Cleaned and trimmed IMDb dataset for faster queries
- Streamlit interface for real-time chat
- Fallback text responses for invalid or failed queries
