import os
import re
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from langchain.schema import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from dotenv import load_dotenv
load_dotenv()
# ─── CONFIGURATION ─────────────────────────────────────────────────────────
os.environ["GOOGLE_API_KEY"] = "AIzaSyBPePlwvbmwornv2Y1HHhZntYuxlhsE38U"
PDF_PATH = "data/Income_Tax_Rules_1962_amended.pdf"
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "tax_rules_amended"

# ─── 1. OCR TEXT EXTRACTION ────────────────────────────────────────────────
doc = fitz.open(PDF_PATH)
raw_docs = []

for i, page in enumerate(doc):
    pix = page.get_pixmap()
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    text = pytesseract.image_to_string(img)

    if len(text.strip()) > 50:
        raw_docs.append(Document(page_content=text, metadata={"page": i + 1}))

print(f"✓ Extracted {len(raw_docs)} pages with OCR")

# ─── 2. CHUNK TEXT ─────────────────────────────────────────────────────────
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=150,
)

chunked_docs = text_splitter.split_documents(raw_docs)
print(f"✓ Chunked into {len(chunked_docs)} blocks")

# ─── 3. METADATA TAGGING ───────────────────────────────────────────────────
for doc in chunked_docs:
    doc.metadata.update({
        "source": "income-tax-rules-amended-2024",
        "type": "rule_amendment",
        "jurisdiction": "INDIA",
        "amended": True
    })

    match = re.search(r"(?:in\s+)?rule\s+(\d+[A-Za-z]*)", doc.page_content, re.IGNORECASE)
    if match:
        doc.metadata["rule"] = match.group(1).upper()

print("✓ Metadata tagging complete")

# ─── 4. EMBEDDING + INGESTION ──────────────────────────────────────────────
embedder = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

vector_store = QdrantVectorStore.from_documents(
    documents=[],
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        collection_name=COLLECTION_NAME,
        embedding=embedder
)

vector_store.add_documents(chunked_docs)

print("✅ OCR-based ingestion complete!")
