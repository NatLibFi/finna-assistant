import os
from openai import AzureOpenAI
import gradio as gr
import json
import finna_client

client = AzureOpenAI(
  azure_endpoint="https://finna-ai-test.openai.azure.com/",
  api_key=os.getenv("AZURE_OPENAI_KEY"),  
  api_version="2024-02-15-preview"
)

finna = finna_client.FinnaClient()

def search_library_records(search_term, search_type):
    print('search parameters:', search_term, search_type)

    results = finna.search(lookfor=search_term, type=finna_client.FinnaSearchType(search_type))
    return json.dumps(results, indent=2)

tools = [
    {
        "type": "function",
        "function": {
            "name": "search_library_records",
            "description": "Search a library database for records (i.e. books, movies, etc) and their fields (i.e. authors, title, etc)",
            "parameters": {
                "type": "object",
                "properties": {
                    "search_term": {
                        "type": "string",
                        "description": "The search term used to find information about the library records",
                    },
                    "search_type": {
                        "type": "string",
                        "description": "The type of search being done (e.g. title, authors, etc)",
                        "enum": [
                            "AllFields",
                            "Title",
                            "TitleStart",
                            "TitleExact",
                            "Author",
                            "Subject",
                            "description",
                            "geographic",
                            "Classification",
                            "Identifier",
                            "Series",
                            "toc",
                            "publisher",
                            "PublicationPlace",
                            "year",
                            "Holdings"
                        ]
                    }
                },
                "required": ["search_term"],
            },
        },
    }
]

available_functions = {
    "search_library_records": search_library_records
}

def predict(message, chat_history):
    print("-----")
    chat_history.append({"role": "user", "content": message})
    response = client.chat.completions.create(
        model="gpt-35-turbo-16k-0613",
        messages=chat_history,
        tools=tools,
        tool_choice="auto",
        temperature=0.7,
        max_tokens=800,
        top_p=0.95,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None
    )

    response_message = response.choices[0].message
    chat_history.append(response_message)

    print("response:\n", response_message)

    tool_calls = response_message.tool_calls
    if tool_calls:
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_to_call = available_functions[function_name]
            function_args = json.loads(tool_call.function.arguments)

            function_response = function_to_call(
                search_term=function_args.get("search_term"),
                search_type=function_args.get("search_type")
            )

            chat_history.append(
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_response,
                }
            )
        second_response = client.chat.completions.create(
            model="gpt-35-turbo-16k-0613",
            messages=chat_history,
        )
        return {
            "message": second_response.choices[0].message.content,
            "chat_history": chat_history
        }
    
    return {
        "message": response.choices[0].message.content,
        "chat_history": chat_history
    }

initial_chat_history = {
    "role": "system",
    "content": "You are an assistant designed to help users find information about library records."
}

with gr.Blocks() as app:
    # Session state
    chat_history_var = gr.State([initial_chat_history])

    # UI components
    chatbot = gr.Chatbot()
    msg = gr.Textbox()
    with gr.Row():
        with gr.Column(scale=1):
            clear = gr.ClearButton(components=[msg, chatbot])
        with gr.Column(scale=1):
            btn = gr.Button(value="Submit", variant="primary")

    # Function to be called on submit
    def respond(message, chat_component_history, chat_history):
        bot_response = predict(message, chat_history)

        chat_component_history.append((message, bot_response["message"]))

        return {
            msg: "",
            chatbot: chat_component_history,
            chat_history_var: bot_response["chat_history"]
        }

    # Event listeners
    msg.submit(respond, [msg, chatbot, chat_history_var], [msg, chatbot, chat_history_var])
    btn.click(respond, [msg, chatbot, chat_history_var], [msg, chatbot, chat_history_var])
    clear.click(lambda _: [initial_chat_history], [chat_history_var], [chat_history_var])

if __name__ == "__main__":
    app.launch()