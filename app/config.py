import os
from dotenv import load_dotenv
from langchain_nomic import NomicEmbeddings
from supabase.client import Client, create_client
from langchain.chat_models import init_chat_model

# Load environment variables
load_dotenv()

# Supabase configuration
supabase_url: str | None = os.getenv("SUPABASE_URL")
supabase_key: str | None = os.getenv("SUPABASE_KEY")
if supabase_url and supabase_key:
    supabase: Client = create_client(supabase_url, supabase_key)

# Embedding model configuration
embedding_model = NomicEmbeddings(
    model='nomic-embed-text-v1.5',
    inference_mode='remote',
    nomic_api_key=os.getenv('NOMIC_API_KEY')
)

# Groq model initialization
groq_llm = init_chat_model( 
    model="deepseek-r1-distill-llama-70b", 
    model_provider="groq",
    temperature=0.5
)
