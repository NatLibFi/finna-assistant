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
df = pd.read_csv("organizations.csv", delimiter=";")
# Get embeddings for organization names
df["embedding"] = df["translated"].apply(lambda x: get_embedding(x))

# Save organizations and their embeddings to a .pkl file
df.to_pickle("organizations_embeddings.pkl")
