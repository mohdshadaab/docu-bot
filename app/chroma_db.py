import chromadb
from sentence_transformers import SentenceTransformer
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

class ChromaDBHandler:
    def __init__(self, db_path="../chroma_db", model_name="all-MiniLM-L6-v2"):
        # Initialize the Persistent ChromaDB Client
        self.client = chromadb.PersistentClient(path=db_path)

        # Initialize the Embedding Model
        self.embedding_model = HuggingFaceEmbeddings(model_name=model_name)

        # Initialize all framework indices at once
        self.indices = {
            "FastAPI": self._create_chroma_index("FastAPI"),
            "Django": self._create_chroma_index("Django"),
            "RubyOnRails": self._create_chroma_index("RubyOnRails"),
            "Flutter": self._create_chroma_index("Flutter")
        }

    def _create_chroma_index(self, collection_name):
        # Create and return a Chroma index for the given collection name
        return Chroma(
            collection_name=collection_name,
            embedding_function=self.embedding_model,
            client=self.client
        )

    def get_index(self, framework) -> Chroma:
        # Get the Chroma index for a specific framework
        return self.indices.get(framework, None)

    def query_vectorstore(self, query_text, framework, top_k=5):
        try:
            print(f"Generating embedding for query: '{query_text}'")
            vectorstore = self.get_index(framework, None)

            if vectorstore:
                # Query the vectorstore for similar documents
                results = vectorstore.similarity_search(query_text, top_k)
                return results
            else:
                raise ValueError(f"Framework '{framework}' is not supported.")
        except Exception as e:
            print(e)
            return None
