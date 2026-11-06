
# Clinical Document Intelligence Platform

A full-stack AI-powered application that analyzes synthetic clinical documents, generates structured summaries, and answers document-specific questions using Google Gemini.

Built with React, TypeScript, Python, FastAPI, and PostgreSQL.

## Features

- PDF document upload and text extraction
- AI-powered clinical document summarization
- Document-grounded question answering
- Persistent document and conversation history
- PostgreSQL-backed summary caching to reduce repeated AI requests
- Document management with deletion and confirmation
- Responsive React dashboard
- RESTful APIs with FastAPI
- Error handling and document validation

## Tech Stack

### Frontend
- React
- TypeScript
- Vite
- CSS
- React Markdown

### Initialize the Database

Create a PostgreSQL database named `clinical_document_db`.

After configuring the `DATABASE_URL` environment variable, run the following command from the `backend` directory:

```powershell
.\.venv\Scripts\python.exe init_db.py
```

This creates the required `documents` and `document_questions` tables if they do not already exist.

Existing database records will not be deleted.


### Backend
- Python
- FastAPI
- SQLAlchemy
- PyMuPDF
- Google Gemini API

### Database
- PostgreSQL

### Development Tools
- Git and GitHub
- VS Code
- Swagger UI

## Architecture

React Frontend
    |
    v
FastAPI REST API
    |
    +-- PDF Processing (PyMuPDF)
    |
    +-- Google Gemini API
    |
    +-- SQLAlchemy
            |
            v
        PostgreSQL

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /documents/upload | Upload a PDF |
| GET | /documents | Retrieve document history |
| GET | /documents/{document_id}/text | Extract document text |
| POST | /documents/{document_id}/summarize | Generate or retrieve cached summary |
| POST | /documents/{document_id}/ask | Ask AI about a document |
| GET | /documents/{document_id}/questions | Retrieve saved Q&A history |
| DELETE | /documents/{document_id} | Delete a document and its history |

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js
- PostgreSQL
- Google Gemini API key

### Backend Setup

1. Navigate to the backend directory:

   cd backend

2. Create a virtual environment:

   python -m venv .venv

3. Install dependencies:

   .venv\Scripts\python.exe -m pip install -r requirements.txt

4. Configure environment variables:

   GEMINI_API_KEY=your_api_key
   DATABASE_URL=postgresql+psycopg://username:password@localhost:5432/clinical_document_db

5. Start the backend:

   .venv\Scripts\python.exe -m uvicorn app.main:app --reload

Backend API documentation:

http://127.0.0.1:8000/docs

### Frontend Setup

1. Navigate to the frontend directory:

   cd frontend

2. Install dependencies:

   npm install

3. Start the development server:

   npm run dev

Open the local URL displayed by Vite.

## Database

The application uses PostgreSQL with two primary tables:

- documents: Stores uploaded document metadata, summaries, and processing information.
- document_questions: Stores document-specific questions and AI-generated answers.

## AI Processing Workflow

1. User uploads a synthetic clinical PDF.
2. FastAPI validates and stores the document.
3. PyMuPDF extracts text from the PDF.
4. Gemini generates a structured clinical summary.
5. The summary is cached in PostgreSQL.
6. Users ask questions grounded in the document.
7. Questions and answers are saved for future retrieval.

## Safety and Limitations

This application is intended for educational and demonstration purposes.

- Use synthetic medical documents only.
- AI-generated content may contain errors and requires professional verification.
- Not intended for clinical diagnosis or patient-care decisions.
- Not configured for production handling of protected health information.
- Source page references are AI-generated and are not independently verified.

## Future Enhancements

- User authentication and authorization
- Database migrations with Alembic
- Automated testing
- Cloud deployment
- Improved document search
- More robust document processing and cleanup