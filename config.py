from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
import pinecone
pinecone.init(api_key="4bdfcfb1-fbce-4b38-be35-080b6c96dce4", environment="us-west1-gcp")
index = pinecone.Index("example-trial")