import os
import re
import fitz  # PyMuPDF for PDFs
import docx  # python-docx for DOCX
import requests  # ✅ For Bing image API

from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, ID
from whoosh.qparser import QueryParser

# Define schema: each document has a title (filename) and content
schema = Schema(title=ID(stored=True), content=TEXT(stored=True))

# Set up index directory
index_dir = "indexdir"
if not os.path.exists(index_dir):
    os.mkdir(index_dir)

# Create or open the index
if not os.listdir(index_dir):  # Check if the directory is empty
    index = create_in(index_dir, schema)
else:
    index = open_dir(index_dir)

# Folder containing documents
doc_folder = r"C:\Users\user\MiniSearchEngine\documents"

# Ensure documents exist
if not os.path.exists(doc_folder):
    raise FileNotFoundError(f"❌ Folder not found: {doc_folder}")

# Function to extract text from PDFs
def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        with fitz.open(pdf_path) as doc:
            for page in doc:
                page_text = page.get_text("text")
                text += page_text if page_text else ""
    except Exception as e:
        print(f"⚠️ Error reading {pdf_path}: {e}")
    return text.strip()

# Function to extract text from DOCX
def extract_text_from_docx(docx_path):
    text = ""
    try:
        doc = docx.Document(docx_path)
        text = "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        print(f"⚠️ Error reading {docx_path}: {e}")
    return text.strip()

# Function to index documents
def index_documents():
    writer = index.writer()
    
    for filename in os.listdir(doc_folder):
        file_path = os.path.join(doc_folder, filename)
        content = ""

        if filename.lower().endswith(".txt"):
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read().strip()
        elif filename.lower().endswith(".pdf"):
            content = extract_text_from_pdf(file_path)
        elif filename.lower().endswith(".docx"):
            content = extract_text_from_docx(file_path)

        if content:
            print(f"Indexing: {filename} -> {content[:100]}...")  # Print first 100 chars of the content
            writer.add_document(title=filename, content=content)
    
    writer.commit()
    print("✅ Documents Indexed Successfully!")

# Function to extract snippet with highlighted search term
def extract_snippet(text, query):
    query_words = query.lower().split()
    for word in query_words:
        match = re.search(rf"(.{{0,30}}\b{word}\w*\b.{{0,30}})", text, re.IGNORECASE)
        if match:
            snippet = match.group(0)
            return re.sub(rf"\b{word}\w*\b", lambda m: f'**{m.group(0)}**', snippet)  # Highlight occurrences
    return "🔹 No snippet available."

# Function to perform search
def search_query(query):
    print(f"📥 Received query: {query}")
    with index.searcher() as searcher:
        query_parser = QueryParser("content", index.schema)
        parsed_query = query_parser.parse(query)
        results = searcher.search(parsed_query, limit=10)

        print(f"🔍 Found {len(results)} result(s) for '{query}'")
        for r in results:
            print(f"➡️  Match: {r['title']}")

        return [(result["title"], extract_snippet(result["content"], query)) for result in results]

# ✅ ✅ ✅ Function for Bing Visual Search
BING_API_KEY = "cbb9aaa8eda46eefad95434407bf40cc"
BING_ENDPOINT = "https://api.bing.microsoft.com/v7.0/images/visualsearch"

def search_bing_images(image_path):
    headers = {
        "Ocp-Apim-Subscription-Key": BING_API_KEY,
    }
    files = {
        "image": open(image_path, "rb"),
    }

    try:
        response = requests.post(BING_ENDPOINT, headers=headers, files=files)
        print(f"\n[DEBUG] Status Code: {response.status_code}")
        print(f"[DEBUG] Response Text: {response.text[:500]}...\n")  # Shortened for terminal

        response.raise_for_status()
        data = response.json()

        tags = data.get("tags", [])
        similar_images = []
        for tag in tags:
            actions = tag.get("actions", [])
            for action in actions:
                if action.get("actionType") == "VisualSearch":
                    results = action.get("data", {}).get("value", [])
                    for result in results:
                        if "thumbnailUrl" in result:
                            similar_images.append(result["thumbnailUrl"])
        return similar_images[:8]
    except Exception as e:
        print(f"[Bing Search Error] {e}")
        return []

# CLI for testing (text search only)
if __name__ == "__main__":
    print("📌 Indexing documents...")
    index_documents()
    
    print("📌 Search Engine is running... (type 'exit' to quit)\n")
    
    while True:
        query = input("\n🔎 Enter search query: ").strip()
        if query.lower() == "exit":
            print("📌 Exiting search engine. Goodbye! 🚀")
            break
        
        results = search_query(query)

        if results:
            print(f"\n📌 **Search Results for:** `{query}`")
            print(f"📂 **Total Documents Found:** {len(results)}\n")

            for doc, snippet in results:
                print(f"  📝 **{doc}**")  
                print(f"    ✨ {snippet}\n")
        else:
            print("\n❌ **No matching documents found.** Try different keywords or phrases.")
