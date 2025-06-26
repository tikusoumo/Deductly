import os
import re
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from pathlib import Path

from langchain.schema import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from dotenv import load_dotenv
load_dotenv()
# ─── CONFIG ────────────────────────────────────────────────────────────────
os.environ["GOOGLE_API_KEY"] = "AIzaSyBPePlwvbmwornv2Y1HHhZntYuxlhsE38U"
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "itr_forms"

# List of ITR Form PDFs
form_files = [
    Path("data/ITR1(Sahaj).pdf"),
    Path("data/ITR1-Form.pdf")  # if you have the standard version
]

# ─── OCR + INGEST FUNCTION ─────────────────────────────────────────────────
def ingest_itr_forms(files):
    all_docs = []

    for file_path in files:
        if not file_path.exists():
            print(f"⚠️ Skipping: {file_path}")
            continue

        print(f"📄 OCR Processing: {file_path.name}")
        doc = fitz.open(str(file_path))

        for i, page in enumerate(doc):
            pix = page.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text = pytesseract.image_to_string(img)

            if len(text.strip()) > 50:
                all_docs.append(Document(
                    page_content=text,
                    metadata={
                        "page": i + 1,
                        "type": "form",
                        "form_name": "ITR-1",
                        "source": file_path.name,
                        "jurisdiction": "INDIA",
                        "year": "2024"
                    }
                ))

    print(f"✓ OCR extracted {len(all_docs)} pages")

    # ─── CHUNKING ───────────────────────────────────────────────────────────
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    chunks = splitter.split_documents(all_docs)

    for doc in chunks:
        # Try to extract schedule or section
        sched_match = re.search(r"(Schedule\s+\w+)", doc.page_content, re.IGNORECASE)
        section_match = re.search(r"Section\s+(\d+[A-Za-z]*)", doc.page_content, re.IGNORECASE)

        if sched_match:
            doc.metadata["schedule"] = sched_match.group(1).upper()
        if section_match:
            doc.metadata["section"] = section_match.group(1).upper()

    print(f"✓ Chunked {len(chunks)} blocks")

    # ─── VECTOR STORE INGESTION ─────────────────────────────────────────────
    embedder = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

    vector_store = QdrantVectorStore.from_documents(
        documents=[],
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        collection_name=COLLECTION_NAME,
        embedding=embedder
    )

    vector_store.add_documents(chunks)
    print(f"✅ Ingested {len(chunks)} chunks into '{COLLECTION_NAME}'\n")

# ─── RUN ───────────────────────────────────────────────────────────────────
ingest_itr_forms(form_files)
