# ingest_income_tax_law.py

import os
import re
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain.schema import Document
from openai import OpenAI
from qdrant_client.http import models as qdrant_models
from dotenv import load_dotenv
load_dotenv()
# ─── CONFIGURATION ─────────────────────────────────────────────────────────
os.environ["GOOGLE_API_KEY"] = "AIzaSyBPePlwvbmwornv2Y1HHhZntYuxlhsE38U"

PDF_PATH = Path(__file__).parent / "data/Income-tax-bill-2025.pdf"
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "tax_law_chunks"

# ─── 1. LOAD PDF ───────────────────────────────────────────────────────────
loader = PyPDFLoader(str(PDF_PATH))
raw_docs = loader.load()  # List[Document] with .page_content and .metadata.page
print(f"✓ Loaded {len(raw_docs)} pages from PDF")

# ─── 2. COMBINE ALL PAGES THEN SPLIT BY SECTION ───────────────────────────

full_text = "\n".join([doc.page_content for doc in raw_docs])
full_doc = Document(page_content=full_text, metadata={"source": "income-tax-bill-2025"})

def split_by_section(doc: Document):
    text = doc.page_content

    # Case-insensitive split at all section headers
    parts = re.split(r'(?i)(\bSection\s+\d+[A-Za-z]*)', text)
    out = []

    for i in range(1, len(parts), 2):
        raw_header = parts[i].strip()
        raw_body = parts[i + 1].strip() if i + 1 < len(parts) else ""

        if len(raw_body) < 30:
            continue

        # Normalize section ID: remove 'Section', strip, uppercase
        section_id = (
            raw_header.replace("Section", "")
                      .replace("\n", "")
                      .replace("\r", "")
                      .strip()
                      .upper()
        )

        out.append({
            "section": section_id,
            "text": raw_body,
            "page": None
        })

    print(f"✓ Extracted {len(out)} section blocks.")
    return out

section_chunks = split_by_section(full_doc)
print(f"✓ Splitted {len(section_chunks)} sections from full PDF")

# Log a few for verification
print("👁️ Sample section IDs:", set(sec["section"] for sec in section_chunks[:50]))

# ─── 3. FINE‑GRAIN CHUNKING ─────────────────────────────────────────────────
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=150,
)

fine_chunks = []
for sec in section_chunks:
    temp_doc = Document(
        page_content=sec["text"],
        metadata={
            "source": "income-tax-bill-2025",
            "type": "law",
            "section": sec["section"],
            "page": sec["page"],
        }
    )
    splits = text_splitter.split_documents([temp_doc])
    fine_chunks.extend(splits)
print(f"✓ Splitted {len(fine_chunks)} chunks from sections")
# ─── 4. METADATA ENRICHMENT (Clause Extraction) ────────────────────────────
def extract_clause(text: str):
    match = re.search(r'\((\w+)\)', text)
    return match.group(1) if match else None

for chunk in fine_chunks:
    clause = extract_clause(chunk.page_content)
    if clause:
        chunk.metadata["clause"] = clause

print(f"✓ Enriched {len(fine_chunks)} chunks with clauses")
# # ─── 5. VECTOR STORE INGESTION ──────────────────────────────────────────────
embedder = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004"
)

vector_store = QdrantVectorStore.from_documents(
    documents=[],
    url=QDRANT_URL,
    api_key = QDRANT_API_KEY,
    collection_name=COLLECTION_NAME,
    embedding=embedder
)

vector_store.add_documents(fine_chunks)

print("✅ Ingestion complete!")

# retriever = QdrantVectorStore.from_existing_collection(
#     url=QDRANT_URL,
#     collection_name=COLLECTION_NAME,
#     embedding=embedder
# )


# relevant_chunks = retriever.similarity_search(
#     query="What deductions are available to salaried employees?",
#     k=5,
# )

# for i, doc in enumerate(relevant_chunks):
#     print(f"🔹 Chunk {i+1}")
#     print("Metadata:", doc.metadata)
#     print("Preview:", doc.page_content[:300], "\n")
    
