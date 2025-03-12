import faiss
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel
import os
import time
import pdb

class FaissHNSWSearcher:
    def __init__(self, model_name, index_path, doc_ids_path, device="auto"):
        """
        Initialize the FAISS HNSW Searcher.
        
        :param model_name: Name of the transformer model for embeddings.
        :param index_path: Path to the FAISS index file.
        :param doc_ids_path: Path to the saved document IDs file.
        :param device: Device to load the model ("auto", "cpu", or "cuda").
        """
        self.model_name = model_name
        self.index_path = index_path
        self.doc_ids_path = doc_ids_path
        self.device = device
        
        # Load tokenizer and model
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModel.from_pretrained(self.model_name, device_map=self.device)
        
        # Load FAISS index
        self.index = self._load_faiss_index()
        
        # Load document IDs
        self.doc_ids = self._load_doc_ids()
    
    def _load_faiss_index(self):
        """ Load the FAISS HNSW index from disk."""
        if not os.path.exists(self.index_path):
            raise FileNotFoundError(f"FAISS index file not found at {self.index_path}")
        print(f"Loading FAISS index from {self.index_path}...")
        return faiss.read_index(self.index_path)
    
    def _load_doc_ids(self):
        """ Load document IDs from disk."""
        if not os.path.exists(self.doc_ids_path):
            raise FileNotFoundError(f"Document IDs file not found at {self.doc_ids_path}")
        print(f"Loading document IDs from {self.doc_ids_path}...")
        return np.load(self.doc_ids_path)
    
    def get_dense_embedding(self, text):
        """ Compute dense embedding for a query using the transformer model. """
        batch_dict = self.tokenizer(text, padding=True, truncation=True, return_tensors="pt").to(self.model.device)
        with torch.no_grad():
            outputs = self.model(**batch_dict)
            embedding = outputs.last_hidden_state[:, 0, :]  # CLS token embedding
        return embedding.cpu().numpy()
    
    def search(self, query, top_k=5, threads=8):
        """
        Perform a search using the FAISS HNSW index.
        
        :param query: Input query string.
        :param top_k: Number of nearest neighbors to retrieve.
        :return: List of (doc_id, similarity_score) tuples.
        """
        query_embedding = self.get_dense_embedding(query).astype(np.float32)
        
        # Normalize for cosine similarity
        faiss.normalize_L2(query_embedding)

        faiss.omp_set_num_threads(threads)
        
        D, I = self.index.search(query_embedding, top_k)  # D = similarity scores, I = doc indices
        
        # Retrieve document IDs
        results = [(self.doc_ids[idx], D[0][i]) for i, idx in enumerate(I[0])]
        return results

# Example usage
if __name__ == "__main__":
    output_dir = "code/data/local_index_search/scifact/dense"
    index_path = f"{output_dir}/faiss_hnsw_index.bin"
    doc_ids_path = f"{output_dir}/doc_ids.npy"
    
    searcher = FaissHNSWSearcher(model_name="intfloat/multilingual-e5-large-instruct", 
                                 index_path=index_path, 
                                 doc_ids_path=doc_ids_path)
    
    query = "How does white matter develop in the human brain?"
    time_start = time.time()
    top_results = searcher.search(query, top_k=5)
    time_end = time.time()
    print(f"\n⏱️ Search time: {time_end - time_start:.4f} seconds")
    
    pdb.set_trace()
    print("\n🔍 Top Search Results:")
    for doc_id, score in top_results:
        print(f"📄 Doc ID: {doc_id} | 🔢 Normalizaed L2 Distance Score: {score:.4f}")
    