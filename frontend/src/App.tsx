
import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import "./App.css";

type UploadResponse = {
  document_id: string;
};

type SummaryResponse = {
  document_id: string;
  page_count: number;
  original_characters: number;
  summary: string;
  model: string;
  status: string;
};

type QuestionResponse = {
  document_id: string;
  question: string;
  answer: string;
  page_count: number;
  model: string;
  status: string;
};

type ChatMessage = {
  id?: string;
  question: string;
  answer: string;
  created_at?: string;
};

type QuestionHistoryResponse = {
  document_id: string;
  total_questions: number;
  questions: ChatMessage[];
};

type DocumentRecord = {
  document_id: string;
  filename: string;
  file_size: number;
  status: string;
  uploaded_at: string;
};

type DocumentHistoryResponse = {
  total_documents: number;
  documents: DocumentRecord[];
};

async function getErrorMessage(response: Response): Promise<string> {
  try {
    const data = await response.json();

    if (typeof data.detail === "string") {
      return data.detail;
    }
  } catch {
    // Use the HTTP status if no error detail is available.
  }

  return `Request failed with status ${response.status}`;
}

function App() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const [question, setQuestion] = useState("");
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [asking, setAsking] = useState(false);
  const [questionError, setQuestionError] = useState("");
  const [questionsLoading, setQuestionsLoading] = useState(false);

  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState("");

  const loadDocumentHistory = async () => {
    setHistoryLoading(true);
    setHistoryError("");

    try {
      const response = await fetch("/documents");

      if (!response.ok) {
        throw new Error(await getErrorMessage(response));
      }

      const result: DocumentHistoryResponse = await response.json();
      setDocuments(result.documents);
    } catch (err) {
      setHistoryError(
        err instanceof Error
          ? err.message
          : "Unable to load document history."
      );
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    void loadDocumentHistory();
  }, []);

  const loadQuestionHistory = async (id: string) => {
    setQuestionsLoading(true);
    setQuestionError("");

    try {
      const response = await fetch(`/documents/${id}/questions`);

      if (!response.ok) {
        throw new Error(await getErrorMessage(response));
      }

      const result: QuestionHistoryResponse = await response.json();

      setChatHistory(result.questions);
    } catch (err) {
      setQuestionError(
        err instanceof Error
          ? `Unable to load question history: ${err.message}`
          : "Unable to load question history."
      );
    } finally {
      setQuestionsLoading(false);
    }
  };

  const generateSummary = async (id: string) => {
    const response = await fetch(`/documents/${id}/summarize`, {
      method: "POST",
    });

    if (!response.ok) {
      throw new Error(await getErrorMessage(response));
    }

    const result: SummaryResponse = await response.json();

    setDocumentId(id);
    setSummary(result);
    setMessage("Clinical summary generated successfully.");

    await loadQuestionHistory(id);
  };

  const handleAnalyze = async () => {
    if (!selectedFile || loading || asking) return;

    if (
      selectedFile.type !== "application/pdf" &&
      !selectedFile.name.toLowerCase().endsWith(".pdf")
    ) {
      setError("Please select a PDF document.");
      return;
    }

    if (selectedFile.size > 10 * 1024 * 1024) {
      setError("The PDF must be 10 MB or smaller.");
      return;
    }

    setLoading(true);
    setError("");
    setSummary(null);
    setDocumentId(null);
    setChatHistory([]);
    setQuestion("");
    setQuestionError("");
    setMessage("Uploading document...");

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const uploadResponse = await fetch("/documents/upload", {
        method: "POST",
        body: formData,
      });

      if (!uploadResponse.ok) {
        throw new Error(await getErrorMessage(uploadResponse));
      }

      const uploaded: UploadResponse = await uploadResponse.json();

      if (!uploaded.document_id) {
        throw new Error("The server did not return a document ID.");
      }

      await loadDocumentHistory();

      setMessage("Generating clinical summary with Gemini...");
      await generateSummary(uploaded.document_id);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "An unexpected error occurred."
      );
      setMessage("");
    } finally {
      setLoading(false);
    }
  };

  const handleSelectDocument = async (document: DocumentRecord) => {
    if (loading || asking) return;

    setLoading(true);
    setError("");
    setMessage(`Loading ${document.filename}...`);
    setSummary(null);
    setDocumentId(null);
    setSelectedFile(null);
    setChatHistory([]);
    setQuestion("");
    setQuestionError("");

    try {
      await generateSummary(document.document_id);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load the selected document."
      );
      setMessage("");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteDocument = async (document: DocumentRecord) => {
    if (loading || asking || historyLoading) return;

    const confirmed = window.confirm(
      `Are you sure you want to delete "${document.filename}"?\n\nThis will permanently remove the document and its saved AI conversations.`
    );

    if (!confirmed) return;

    setHistoryLoading(true);
    setHistoryError("");

    try {
      const response = await fetch(
        `/documents/${document.document_id}`,
        {
          method: "DELETE",
        }
      );

      if (!response.ok) {
        throw new Error(await getErrorMessage(response));
      }

      setDocuments((previous) =>
        previous.filter(
          (item) => item.document_id !== document.document_id
        )
      );

      if (documentId === document.document_id) {
        setDocumentId(null);
        setSummary(null);
        setChatHistory([]);
        setQuestion("");
        setQuestionError("");
        setMessage("");
      }
    } catch (err) {
      setHistoryError(
        err instanceof Error
          ? err.message
          : "Unable to delete document."
      );
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleAskQuestion = async () => {
    const trimmedQuestion = question.trim();

    if (
      !documentId ||
      !trimmedQuestion ||
      asking ||
      loading ||
      questionsLoading
    ) {
      return;
    }

    setAsking(true);
    setQuestionError("");

    try {
      const response = await fetch(`/documents/${documentId}/ask`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: trimmedQuestion,
        }),
      });

      if (!response.ok) {
        throw new Error(await getErrorMessage(response));
      }

      const result: QuestionResponse = await response.json();

      setChatHistory((previous) => [
        ...previous,
        {
          question: result.question,
          answer: result.answer,
        },
      ]);

      setQuestion("");
    } catch (err) {
      setQuestionError(
        err instanceof Error
          ? err.message
          : "Unable to answer the question."
      );
    } finally {
      setAsking(false);
    }
  };

  return (
    <div className="app">
      <header className="header">
        <div className="brand">
          <div className="brand-icon">+</div>
          <div>
            <h1>Clinical Document Intelligence</h1>
            <p>AI-Powered Healthcare Document Analysis</p>
          </div>
        </div>
        <span className="demo-badge">Demo Platform</span>
      </header>

      <main className="main">
        <section className="welcome">
          <h2>Clinical Document Dashboard</h2>
          <p>
            Upload a synthetic medical record, generate a clinical summary,
            and ask questions about the document.
          </p>
        </section>

        <div className="dashboard-grid">
          <section className="panel">
            <h3>Upload Medical Document</h3>
            <p className="description">
              Select a PDF containing synthetic patient records.
            </p>

            <div className="upload-box">
              <div className="upload-icon">📄</div>
              <h4>Select a PDF Document</h4>
              <p>Maximum file size: 10 MB</p>

              <input
                type="file"
                accept=".pdf,application/pdf"
                disabled={loading || asking}
                onChange={(event) => {
                  setSelectedFile(event.target.files?.[0] ?? null);
                  setSummary(null);
                  setDocumentId(null);
                  setChatHistory([]);
                  setQuestion("");
                  setMessage("");
                  setError("");
                  setQuestionError("");
                }}
              />
            </div>

            {selectedFile && (
              <div className="file-info">
                <strong>Selected:</strong> {selectedFile.name}
              </div>
            )}

            <button
              className="primary-button"
              disabled={!selectedFile || loading || asking}
              onClick={handleAnalyze}
            >
              {loading ? "Analyzing Document..." : "Analyze Document"}
            </button>

            {message && (
              <p role="status" style={{ color: "#2563eb", marginTop: 16 }}>
                {message}
              </p>
            )}

            {error && (
              <p role="alert" style={{ color: "#dc2626", marginTop: 16 }}>
                {error}
              </p>
            )}
          </section>

          <section className="panel">
            <h3>Clinical Summary</h3>
            <p className="description">
              AI-generated findings will appear here.
            </p>

            {summary ? (
              <div>
                <div className="file-info">
                  <strong>Status:</strong> {summary.status}
                  <p>
                    <strong>Pages:</strong> {summary.page_count}
                  </p>
                  <p>
                    <strong>Model:</strong> {summary.model}
                  </p>
                </div>

                <div className="clinical-markdown">
                  <ReactMarkdown>{summary.summary}</ReactMarkdown>
                </div>
              </div>
            ) : (
              <div className="empty-state">
                <div className="empty-icon">🩺</div>
                <h4>
                  {loading ? "Analyzing Document" : "No Document Analyzed"}
                </h4>
                <p>
                  {loading
                    ? "Please wait while the document is processed."
                    : "Upload a synthetic medical record or select a previously uploaded document to view its clinical summary."}
                </p>
              </div>
            )}
          </section>
        </div>

        <section className="panel history-panel">
          <div className="history-header">
            <div>
              <h3>Document History</h3>
              <p className="description">
                View and analyze previously uploaded documents.
              </p>
            </div>

            <button
              className="history-refresh"
              onClick={() => void loadDocumentHistory()}
              disabled={historyLoading}
            >
              {historyLoading ? "Refreshing..." : "Refresh"}
            </button>
          </div>

          {historyError && (
            <p role="alert" style={{ color: "#dc2626" }}>
              {historyError}
            </p>
          )}

          {historyLoading && documents.length === 0 ? (
            <p className="description">Loading document history...</p>
          ) : documents.length === 0 ? (
            <div className="history-empty">
              No documents uploaded yet.
            </div>
          ) : (
            <div className="document-list">
              {documents.map((document) => (
                <div className="document-item" key={document.document_id}>
                  <div className="document-icon">📄</div>

                  <div className="document-details">
                    <strong>{document.filename}</strong>
                    <p>
                      {(document.file_size / 1024).toFixed(1)} KB
                      {" · "}
                      {new Date(document.uploaded_at).toLocaleString()}
                    </p>
                    <span className="document-status">
                      {document.status}
                    </span>
                  </div>


                <div className="document-actions">
                  <button
                    className="history-action"
                    disabled={loading || asking || historyLoading}
                    onClick={() => void handleSelectDocument(document)}
                  >
                    Analyze
                  </button>

                  <button
                    className="delete-button"
                    disabled={loading || asking || historyLoading}
                    onClick={() => void handleDeleteDocument(document)}
                  >
                    Delete
                  </button>
                </div>

                </div>
              ))}
            </div>
          )}
        </section>

        <section className="panel qa-panel">
          <h3>Ask AI About This Document</h3>
          <p className="description">
            Ask questions about diagnoses, medications, laboratory findings,
            treatment history, or documented follow-up plans.
          </p>

          {!documentId ? (
            <div className="qa-placeholder">
              Analyze a document first to enable AI question-answering.
            </div>
          ) : (
            <>
              <div className="chat-history">
                {questionsLoading ? (
                  <p className="description">
                    Loading previous questions...
                  </p>
                ) : chatHistory.length === 0 ? (
                  <p className="description">
                    No questions asked yet. Try asking:
                    "What medications is the patient currently taking?"
                  </p>
                ) : (
                  chatHistory.map((chat, index) => (
                    <div
                      className="chat-entry"
                      key={chat.id ?? index}
                    >
                      <div className="chat-question">
                        <strong>You asked:</strong>
                        <p>{chat.question}</p>
                      </div>

                      <div className="chat-answer">
                        <strong>AI Answer:</strong>
                        <ReactMarkdown>{chat.answer}</ReactMarkdown>
                      </div>
                    </div>
                  ))
                )}
              </div>

              <div className="question-form">
                <textarea
                  className="question-input"
                  placeholder="Ask a question about the uploaded document..."
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  disabled={asking || loading || questionsLoading}
                  maxLength={1000}
                  rows={3}
                />

                <button
                  className="primary-button"
                  onClick={handleAskQuestion}
                  disabled={
                    !question.trim() ||
                    asking ||
                    loading ||
                    questionsLoading
                  }
                >
                  {asking ? "Generating Answer..." : "Ask AI"}
                </button>
              </div>

              {questionError && (
                <p role="alert" style={{ color: "#dc2626" }}>
                  {questionError}
                </p>
              )}
            </>
          )}
        </section>

        <footer className="footer">
          For demonstration purposes only. AI-generated content
          requires professional verification and must not be used
          for real patient-care decisions.
        </footer>
      </main>
    </div>
  );
}

export default App;
