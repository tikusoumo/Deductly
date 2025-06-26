import os
import re
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain.schema import Document
from dotenv import load_dotenv
load_dotenv()
# ─── CONFIGURATION ─────────────────────────────────────────────────────────
os.environ["GOOGLE_API_KEY"] = "AIzaSyBPePlwvbmwornv2Y1HHhZntYuxlhsE38U"
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

# Capital Gain and Tribunal Ruling PDFs
capital_gain_files = [
    Path("data/Capital_Gain_Tax_Exemption1.pdf"),
    Path("data/Capital_Gain_Tax_Exemption2.pdf"),
    Path("data/Capital_Gain_Tax_Exemption3.pdf")
]

tribunal_files = [
    Path("data/Recent_Tribunal_Rullings1.pdf"),
    Path("data/Recent_Tribunal_Rullings2.pdf"),
    Path("data/Recent_Tribunal_Rullings3.pdf")
]

# ─── FUNCTION: PROCESS PDF GROUP ───────────────────────────────────────────
def process_pdf_group(file_list, collection_name, doc_type, origin_tag):
    all_chunks = []

    for file_path in file_list:
        if not file_path.exists():
            print(f"⚠️ Skipping {file_path.name} (not found)")
            continue

        print(f"📄 Processing: {file_path.name}")
        loader = PyPDFLoader(str(file_path))
        raw_docs = loader.load()

        # Split pages into 1000-char blocks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=150,
        )
        chunks = text_splitter.split_documents(raw_docs)

        for doc in chunks:
            # Base metadata
            doc.metadata.update({
                "source": file_path.name,
                "type": doc_type,
                "origin": origin_tag,
                "jurisdiction": "INDIA"
            })

            # Extract referenced section if found
            section_match = re.search(r"Section\s+(\d+[A-Za-z]*)", doc.page_content, re.IGNORECASE)
            if section_match:
                doc.metadata["section"] = section_match.group(1).upper()

        all_chunks.extend(chunks)
        print(f"→ {len(chunks)} chunks from {file_path.name}")

    # ─── EMBEDDING & INGESTION ──────────────────────────────────────────────
    embedder = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

    vector_store = QdrantVectorStore.from_documents(
        documents=[],
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        collection_name=collection_name,
        embedding=embedder
    )
    vector_store.add_documents(all_chunks)

    print(f"✅ Ingested {len(all_chunks)} chunks into '{collection_name}'\n")


# ─── INGEST CAPITAL GAIN CASES ─────────────────────────────────────────────
process_pdf_group(
    file_list=capital_gain_files,
    collection_name="capital_gain_cases",
    doc_type="case_law",
    origin_tag="ITAT/HC"
)

process_pdf_group(
    file_list=tribunal_files,
    collection_name="tribunal_rulings",
    doc_type="tribunal_ruling",
    origin_tag="ITAT"
)

