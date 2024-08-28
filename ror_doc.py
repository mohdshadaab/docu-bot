import os
import re
import unicodedata
import chromadb
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


# Function to clean text (same as before)
def clean_scraped_content(content):
    # Remove HTML/XML tags
    content = re.sub(r'<[^>]*>', '', content)

    # Remove extra newlines and whitespace
    content = re.sub(r'\s+', ' ', content).strip()

    # Remove the feedback section
    feedback_text = (
        r"Feedback\s+You're encouraged to help improve the quality of this guide.\s+"
        r"Please contribute if you see any typos or factual errors.*?on the official Ruby on Rails Forum\."
    )
    content = re.sub(feedback_text, '', content, flags=re.DOTALL)

    return content

# Initialize ChromaDB Persistent Client
print("Initializing ChromaDB Persistent Client...")
client = chromadb.PersistentClient(path="./chroma_db")
print("ChromaDB Persistent Client initialized.")

# Directory containing the scraped documentation files
docs_folder = 'RoR-Docs'

# Define LangChain text splitter
print("Defining LangChain text splitter...")
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1024, # Size of each chunk in characters
    chunk_overlap=100, # Overlap between consecutive chunks
    length_function=len, # Function to compute the length of the text
  )
print("Text splitter defined.")

# Initialize Hugging Face model for embeddings (all-MiniLM-L6-v2)
print("Initializing SentenceTransformer model for embeddings...")
embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
print("SentenceTransformer model initialized.")

# Initialize Chroma DB in LangChain, connecting it to the PersistentClient
print("Initializing Chroma VectorStore...")
vectorstore = Chroma(
    collection_name="RubyOnRails",
    embedding_function=embedding_model,
    client=client
)
print("Chroma VectorStore initialized.")

# Iterate over each file in the FastAPI-Docs folder
for filename in os.listdir(docs_folder):
    file_path = os.path.join(docs_folder, filename)

    # Process only text files
    if filename.endswith('.txt'):
        print(f"Reading file: {filename}")
        with open(file_path, 'r', encoding='utf-8') as file:
            raw_text = file.read()

        print(f"File read successfully. Length of raw text: {len(raw_text)} characters")

        # Clean the text
        cleaned_text = clean_scraped_content(raw_text)
        print(f"Cleaned text. Length of cleaned text: {len(cleaned_text)} characters")

        # Split text into smaller documents using LangChain's CharacterTextSplitter
        print("Splitting text into smaller chunks...")
        docs = text_splitter.create_documents([cleaned_text])
        print(f"Number of document chunks created: {len(docs)}")

        # Store each document chunk in Chroma DB
        print("Storing document chunks in ChromaDB...")
        for doc in docs:
            metadata = {"source": filename}
            vectorstore.add_texts([doc.page_content], metadatas=[metadata])

        # Automatically persist the Chroma database due to PersistentClient
        print(f"Data persisted successfully after processing {filename}")

print("All files processed and data persisted.")
