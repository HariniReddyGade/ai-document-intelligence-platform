
from fastapi import FastAPI

app = FastAPI(
    title="AI Document Intelligence API",
    description="Backend API for AI-powered document processing and question answering.",
    version="1.0.0"
)


@app.get("/")
def home():
    return {
        "message": "Welcome to the AI Document Intelligence Platform",
        "status": "running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "AI Document Intelligence API"
    }
