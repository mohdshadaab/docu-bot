import os
import re
import pymupdf  # For extracting text from PDF using pymupdf
import unicodedata
import chromadb
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# # Function to clean text (same as before)
# def clean_scraped_content(content):
#     # Remove extra newlines and whitespace
#     content = re.sub(r'\s+', ' ', content).strip()
#     # Optional: Add specific rules for unnecessary blocks if needed
#     return content

# Extract text from a PDF file using pymupdf
def extract_text_from_pdf(pdf_path):
    extracted_text = ""
    doc = pymupdf.open(pdf_path)  # Open the PDF file
    for page in doc:  # Iterate over each page
        extracted_text += page.get_text()  # Get text from each page
    return extracted_text

# Initialize ChromaDB Persistent Client
print("Initializing ChromaDB Persistent Client...")
client = chromadb.PersistentClient(path="./chroma_db")
print("ChromaDB Persistent Client initialized.")

# Define LangChain text splitter
print("Defining LangChain text splitter...")
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1024,  # Size of each chunk in characters
    chunk_overlap=100,  # Overlap between consecutive chunks
    length_function=len,  # Function to compute the length of the text
)
print("Text splitter defined.")

# Initialize Hugging Face model for embeddings (all-MiniLM-L6-v2)
print("Initializing SentenceTransformer model for embeddings...")
embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
print("SentenceTransformer model initialized.")

# Initialize Chroma DB in LangChain, connecting it to the PersistentClient
print("Initializing Chroma VectorStore...")
vectorstore = Chroma(
    collection_name="Django",
    embedding_function=embedding_model,
    client=client
)
print("Chroma VectorStore initialized.")

# Specify the path to the Django documentation PDF
pdf_path = 'django.pdf'

# Extract and process the PDF text using pymupdf
print(f"Extracting text from PDF: {pdf_path}")
pdf_text = extract_text_from_pdf(pdf_path)
print(f"Text extracted from PDF. Length: {len(pdf_text)} characters")

# Clean the extracted text
cleaned_text = pdf_text
print(f"Cleaned text. Length: {len(cleaned_text)} characters")

# Split text into smaller documents using LangChain's CharacterTextSplitter
print("Splitting text into smaller chunks...")
docs = text_splitter.create_documents([cleaned_text])
print(f"Number of document chunks created: {len(docs)}")

# Store each document chunk in Chroma DB
print("Storing document chunks in ChromaDB...")
for doc in docs:
    metadata = {"source": "Django PDF"}
    vectorstore.add_texts([doc.page_content], metadatas=[metadata])

# Automatically persist the Chroma database due to PersistentClient
print("Data persisted successfully after processing the PDF.")
