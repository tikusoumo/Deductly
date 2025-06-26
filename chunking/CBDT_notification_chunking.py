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
# ─── CONFIGURATION ─────────────────────────────────────────────────────────
os.environ["GOOGLE_API_KEY"] = "AIzaSyBPePlwvbmwornv2Y1HHhZntYuxlhsE38U"
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "cbdt_notifications"

notification_files = [
    Path("data/CBDT-Notification-7-2024.pdf"),
    Path("data/CBDT-Notification-9-DV-2016.pdf"),
    Path("data/CBDT-Notification-70-2022.pdf"),
]

# ─── OCR INGESTION ─────────────────────────────────────────────────────────
def ingest_notifications_with_ocr(files):
    all_docs = []

    for file_path in files:
        print(f"📄 OCR Processing: {file_path.name}")
        if not file_path.exists():
            print(f"⚠️ File missing: {file_path}")
            continue

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
                        "source": file_path.name,
                        "type": "notification",
                        "origin": "CBDT",
                        "jurisdiction": "INDIA"
                    }
                ))

    print(f"✓ OCR extracted {len(all_docs)} pages")

    # ─── CHUNKING ───────────────────────────────────────────────────────────
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    chunks = splitter.split_documents(all_docs)

    for doc in chunks:
        match_section = re.search(r"Section\s+(\d+[A-Za-z]*)", doc.page_content, re.IGNORECASE)
        match_clause = re.search(r"\((\d+[a-zA-Z]*)\)", doc.page_content)
        if match_section:
            doc.metadata["section"] = match_section.group(1).upper()
        if match_clause:
            doc.metadata["clause"] = match_clause.group(1)

    print(f"✓ Created {len(chunks)} chunks")

    # ─── EMBEDDING + INGESTION ──────────────────────────────────────────────
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
ingest_notifications_with_ocr(notification_files)
