import os
from openai import AzureOpenAI
import gradio as gr

client = AzureOpenAI(
  azure_endpoint="https://finna-ai-test.openai.azure.com/",
  api_key=os.getenv("AZURE_OPENAI_KEY"),  
  api_version="2024-02-15-preview"
)

def predict(message, history):
    history_openai_format = []
    history_openai_format.append({"role":"system","content":"You are an AI assistant that helps people find information."})
    for human, assistant in history:
        history_openai_format.append({"role": "user", "content": human })
        history_openai_format.append({"role": "assistant", "content":assistant})
    history_openai_format.append({"role": "user", "content": message})
    print(history_openai_format)

    response = client.chat.completions.create(
        model="gpt-35-turbo-16k-0613",
        messages=history_openai_format,
        temperature=0.7,
        max_tokens=800,
        top_p=0.95,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None
    )
    print(response)
    
    return response.choices[0].message.content

gr.ChatInterface(predict).launch()