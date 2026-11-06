
import logging
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .database import get_db
from .gemini_service import summarize_document
from .models import Document, DocumentQuestion
from .pdf_processor import extract_text_from_pdf
from .qa_service import answer_document_question

app = FastAPI(
    title="AI Document Intelligence API",
    description="Backend API for AI-powered document processing and question answering.",
    version="1.0.0"
)

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


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


@app.post("/documents/upload", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed"
        )

    document_uuid = uuid4()
    document_id = str(document_uuid)
    saved_filename = f"{document_id}.pdf"
    file_path = UPLOAD_DIR / saved_filename
    file_size = 0

    try:
        with file_path.open("wb") as destination:
            while chunk := await file.read(1024 * 1024):
                file_size += len(chunk)

                if file_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="File size exceeds the 10 MB limit"
                    )

                destination.write(chunk)

        with file_path.open("rb") as saved_file:
            if saved_file.read(5) != b"%PDF-":
                raise HTTPException(
                    status_code=400,
                    detail="Invalid PDF file"
                )

        document = Document(
            document_id=document_uuid,
            filename=file.filename[:255],
            file_size=file_size,
            status="uploaded"
        )

        db.add(document)
        db.commit()

    except HTTPException:
        db.rollback()
        file_path.unlink(missing_ok=True)
        raise

    except Exception:
        db.rollback()
        file_path.unlink(missing_ok=True)
        logging.exception("Document upload failed")
        raise HTTPException(
            status_code=500,
            detail="Unable to save uploaded document"
        )

    finally:
        await file.close()

    return {
        "message": "PDF uploaded successfully",
        "document_id": document_id,
        "filename": file.filename,
        "file_size_bytes": file_size,
        "status": "uploaded"
    }


@app.get("/documents")
def get_document_history(db: Session = Depends(get_db)):
    documents = (
        db.query(Document)
        .order_by(Document.uploaded_at.desc())
        .all()
    )

    return {
        "total_documents": len(documents),
        "documents": [
            {
                "document_id": str(document.document_id),
                "filename": document.filename,
                "file_size": document.file_size,
                "status": document.status,
                "uploaded_at": document.uploaded_at.isoformat()
            }
            for document in documents
        ]
    }

@app.get("/documents/{document_id}/text")
def get_document_text(document_id: str):
    try:
        document_uuid = str(UUID(document_id))
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid document ID"
        )

    file_path = UPLOAD_DIR / f"{document_uuid}.pdf"

    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    try:
        extracted_data = extract_text_from_pdf(file_path)
    except Exception:
        raise HTTPException(
            status_code=422,
            detail="Unable to extract text from this PDF"
        )

    return {
        "document_id": document_uuid,
        **extracted_data
    }


@app.post("/documents/{document_id}/summarize")
def summarize_uploaded_document(
    document_id: str,
    db: Session = Depends(get_db)
):
    try:
        document_uuid = UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid document ID"
        )

    document = db.get(Document, document_uuid)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    file_path = UPLOAD_DIR / f"{document_uuid}.pdf"

    if document.summary:
        if (
            document.page_count is None
            or document.original_characters is None
        ):
            if file_path.is_file():
                try:
                    extracted_data = extract_text_from_pdf(file_path)

                    document.page_count = extracted_data["page_count"]
                    document.original_characters = extracted_data[
                        "total_characters"
                    ]

                    db.commit()
                except Exception:
                    db.rollback()
                    logging.exception(
                        "Unable to update cached document metadata"
                    )

        return {
            "document_id": str(document_uuid),
            "page_count": document.page_count,
            "original_characters": document.original_characters,
            "summary": document.summary,
            "model": "gemini-3.1-flash-lite",
            "status": "completed",
            "cached": True
        }

    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Document file not found"
        )

    try:
        extracted_data = extract_text_from_pdf(file_path)
    except Exception:
        raise HTTPException(
            status_code=422,
            detail="Unable to process PDF"
        )

    document_text = "\n\n".join(
        page["text"] for page in extracted_data["pages"]
    )

    if not document_text.strip():
        raise HTTPException(
            status_code=422,
            detail="PDF contains no extractable text"
        )

    try:
        summary = summarize_document(document_text)
    except ValueError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error)
        )
    except Exception:
        logging.exception("Gemini summarization failed")
        raise HTTPException(
            status_code=502,
            detail="AI summarization service is unavailable"
        )

    try:
        document.summary = summary
        document.page_count = extracted_data["page_count"]
        document.original_characters = extracted_data["total_characters"]

        db.commit()
    except Exception:
        db.rollback()
        logging.exception("Unable to save document summary")
        raise HTTPException(
            status_code=500,
            detail="Unable to save generated summary"
        )

    return {
        "document_id": str(document_uuid),
        "page_count": document.page_count,
        "original_characters": document.original_characters,
        "summary": summary,
        "model": "gemini-3.1-flash-lite",
        "status": "completed",
        "cached": False
    }


@app.post("/documents/{document_id}/ask")
def ask_document_question(
    document_id: str,
    request: QuestionRequest,
    db: Session = Depends(get_db)
):
    try:
        document_uuid = UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid document ID"
        )

    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=422,
            detail="Question cannot be empty"
        )

    document = db.get(Document, document_uuid)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    file_path = UPLOAD_DIR / f"{document_uuid}.pdf"

    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Document file not found"
        )

    try:
        extracted_data = extract_text_from_pdf(file_path)
    except Exception:
        raise HTTPException(
            status_code=422,
            detail="Unable to process PDF"
        )

    if not any(
        page["text"].strip()
        for page in extracted_data["pages"]
    ):
        raise HTTPException(
            status_code=422,
            detail="PDF contains no extractable text"
        )

    try:
        answer = answer_document_question(
            extracted_data["pages"],
            question
        )
    except ValueError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error)
        )
    except Exception:
        logging.exception("Gemini question answering failed")
        raise HTTPException(
            status_code=502,
            detail="AI question answering service is unavailable"
        )

    try:
        saved_question = DocumentQuestion(
            document_id=document_uuid,
            question=question,
            answer=answer
        )

        db.add(saved_question)
        db.commit()

    except Exception:
        db.rollback()
        logging.exception("Unable to save question history")
        raise HTTPException(
            status_code=500,
            detail="Unable to save question history"
        )

    return {
        "document_id": str(document_uuid),
        "question": question,
        "answer": answer,
        "page_count": extracted_data["page_count"],
        "model": "gemini-3.1-flash-lite",
        "status": "completed"
    }

@app.get("/documents/{document_id}/questions")
def get_document_questions(
    document_id: str,
    db: Session = Depends(get_db)
):
    try:
        document_uuid = UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid document ID"
        )

    document = db.get(Document, document_uuid)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    questions = (
        db.query(DocumentQuestion)
        .filter(DocumentQuestion.document_id == document_uuid)
        .order_by(
            DocumentQuestion.created_at.asc(),
            DocumentQuestion.id.asc()
        )
        .all()
    )

    return {
        "document_id": str(document_uuid),
        "total_questions": len(questions),
        "questions": [
            {
                "id": str(item.id),
                "question": item.question,
                "answer": item.answer,
                "created_at": item.created_at.isoformat()
            }
            for item in questions
        ]
    }

@app.delete("/documents/{document_id}")
def delete_document(
    document_id: str,
    db: Session = Depends(get_db)
):
    try:
        document_uuid = UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid document ID"
        )

    document = db.get(Document, document_uuid)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    file_path = UPLOAD_DIR / f"{document_uuid}.pdf"
    temporary_path = UPLOAD_DIR / f"{document_uuid}.deleting"

    if temporary_path.exists():
        raise HTTPException(
            status_code=409,
            detail="Document deletion is already in progress"
        )

    file_renamed = False

    try:
        if file_path.is_file():
            file_path.rename(temporary_path)
            file_renamed = True

        db.delete(document)
        db.commit()

    except Exception:
        db.rollback()

        if file_renamed:
            try:
                temporary_path.rename(file_path)
            except OSError:
                logging.exception(
                    "Unable to restore PDF after database deletion failure"
                )

        logging.exception("Unable to delete document")
        raise HTTPException(
            status_code=500,
            detail="Unable to delete document"
        )

    if file_renamed:
        try:
            temporary_path.unlink()
        except OSError:
            logging.exception(
                "Database record deleted, but temporary PDF cleanup failed"
            )
            raise HTTPException(
                status_code=500,
                detail=(
                    "Database record was deleted, but PDF cleanup failed. "
                    "Manual cleanup may be required."
                )
            )

    return {
        "document_id": str(document_uuid),
        "status": "deleted",
        "message": "Document and associated database history deleted"
    }
