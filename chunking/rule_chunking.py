import os
import re
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain.schema import Document

# ─── CONFIGURATION ─────────────────────────────────────────────────────────
os.environ["GOOGLE_API_KEY"] = "AIzaSyBPePlwvbmwornv2Y1HHhZntYuxlhsE38U"
PDF_PATH = Path(__file__).parent / "data/Income_Tax_Rules_1962.pdf"
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "tax_rules_chunks"

# ─── 1. LOAD PDF ───────────────────────────────────────────────────────────
loader = PyPDFLoader(str(PDF_PATH))
raw_docs = loader.load()
print(f"✓ Loaded {len(raw_docs)} pages from PDF")

# ─── 2. COMBINE & SPLIT BY RULE ────────────────────────────────────────────
full_text = "\n".join([doc.page_content for doc in raw_docs])
full_doc = Document(page_content=full_text, metadata={"source": "Income_Tax_Rules_1962"})

def split_by_rule(doc: Document):
    text = doc.page_content
    parts = re.split(r'(?i)(\bRule\s+\d+[A-Za-z]*)', text)
    out = []

    for i in range(1, len(parts), 2):
        header = parts[i].strip()
        if i + 1 < len(parts):
            body = parts[i + 1].strip()
        else:
            continue

        if len(body) < 30:
            continue

        rule_id = (
            header.replace("Rule", "")
                  .replace("\n", "")
                  .replace("\r", "")
                  .strip()
                  .upper()
        )

        out.append({
            "rule": rule_id,
            "text": body,
            "page": None
        })

    print(f"✓ Extracted {len(out)} rule blocks.")
    return out

rule_chunks = split_by_rule(full_doc)
print(f"✓ Splitted {len(rule_chunks)} rules from full PDF")
print("👁️ Sample rule IDs:", set(sec["rule"] for sec in rule_chunks[:10]))

# ─── 3. FINE‑GRAIN CHUNKING ─────────────────────────────────────────────────
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=150,
)

fine_chunks = []
for rule in rule_chunks:
    temp_doc = Document(
        page_content=rule["text"],
        metadata={
            "source": "income-tax-rules-1962",
            "type": "rule",
            "rule": rule["rule"],
            "page": rule["page"],
            "jurisdiction": "INDIA"
        }
    )
    splits = text_splitter.split_documents([temp_doc])
    fine_chunks.extend(splits)

print(f"✓ Splitted {len(fine_chunks)} chunks from rules")

# ─── 4. CLAUSE ENRICHMENT ───────────────────────────────────────────────────
def extract_clause(text: str):
    match = re.search(r'\((\w+)\)', text)
    return match.group(1) if match else None

for chunk in fine_chunks:
    clause = extract_clause(chunk.page_content)
    if clause:
        chunk.metadata["clause"] = clause

print(f"✓ Enriched {len(fine_chunks)} chunks with clauses")

# ─── 5. VECTOR STORE INGESTION ──────────────────────────────────────────────
embedder = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

vector_store = QdrantVectorStore.from_documents(
    documents=[],
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
    collection_name=COLLECTION_NAME,
    embedding=embedder
)

vector_store.add_documents(fine_chunks)

print("✅ Ingestion complete!")
