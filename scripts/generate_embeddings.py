import os

from openai import AzureOpenAI
import pandas as pd

client = AzureOpenAI(
    azure_endpoint="https://finna-ai-test.openai.azure.com/",
    api_key=os.getenv("AZURE_OPENAI_KEY"),  
    api_version="2024-02-15-preview"
)

def get_embedding(text):
    return client.embeddings.create(input=text, model="text-embedding-ada-002").data[0].embedding

# Read organizations from file
df_o = pd.read_csv("data/organizations.csv", delimiter=";")
# Get embeddings for organization names
df_o["embedding"] = df_o["translated"].apply(lambda x: get_embedding(x))

# Read journals from file
df_j = pd.read_csv("data/journals.csv")
# Get embeddings for journal names
df_j["embedding"] = df_j["value"].apply(lambda x: get_embedding(x))

# Save embeddings to .pkl files
os.makedirs("embeddings", exist_ok=True)
df_o.to_pickle("embeddings/organizations_embeddings.pkl")
df_j.to_pickle("embeddings/journals_embeddings.pkl")
