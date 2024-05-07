import os
from openai import AzureOpenAI, OpenAIError
import gradio as gr
import json
import finna_client

client = AzureOpenAI(
  azure_endpoint="https://finna-ai-test.openai.azure.com/",
  api_key=os.getenv("AZURE_OPENAI_KEY"),  
  api_version="2024-02-15-preview"
)

finna = finna_client.FinnaClient()

def search_library_records(search_term, search_type, formats, year_from, year_to, language):
    print('search parameters:', search_term, search_type, formats, year_from, year_to, language)

    # Set format filter
    if (type(formats) != list):
        formats = [formats]
    format_filter = ["~format:\"0/" + f + "/\"" for f in formats] if formats[0] else []

    # Set date range filter
    date_from = str(year_from) if year_from else "*"
    date_to = str(year_to) if year_to else "*"
    date_range_filter = "search_daterange_mv:\"[" + date_from + " TO " + date_to + "]\""
    
    # Set language filter
    language_filter = "~language:\"" + language + "\"" if language else None
    
    filters = []
    filters += format_filter
    filters += [date_range_filter]
    filters += [language_filter]
    print(filters)

    results = finna.search(lookfor=search_term, type=finna_client.FinnaSearchType(search_type), filters=filters)
    return json.dumps(results, indent=2)

tools = [
    {
        "type": "function",
        "function": {
            "name": "search_library_records",
            "description": "Search a library database for records (i.e. books, movies, etc) and their fields (i.e. authors, title, etc).",
            "parameters": {
                "type": "object",
                "properties": {
                    "search_term": {
                        "type": "string",
                        "description": "The search term used to find information about the library records.",
                    },
                    "search_type": {
                        "type": "string",
                        "description": "The type of field being searched (e.g. title, author, etc). Only use the options given.",
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
                    },
                    "formats": {
                        "type": "array",
                        "description": "Array of format filters used to limit search results by record type. \
                                        For example using [\"Book\", \"Image\"] to only search for books and images. \
                                        You can use multiple filters at once. \
                                        Only use the options given.",
                        "items": {
                            "type": "string",
                            "description": "Record format type being filtered",
                            "enum": [
                                "Book",
                                "Journal",
                                "Document",
                                "Image",
                                "Thesis",
                                "Sound",
                                "PhysicalObject",
                                "OtherText",
                                "MusicalScore",
                                "Video",
                                "Other",
                                "Map",
                                "WorkOfArt",
                                "Game",
                                "Place",
                                "LearningMaterial",
                                "AIPA",
                                "Unknown",
                                "G1",
                                "frågelistsvar",
                                "offentliggjord inspelning"
                            ]
                        }
                    },
                    "year_from": {
                        "type": "integer",
                        "description": "First year of the date range the search is limited to. \
                                        For example 2020 when searching for records published since 2020. \
                                        Use negative numbers for years before the Common Era, for example -1000 for 1000BCE."
                    },
                    "year_to": {
                        "type": "integer",
                        "description": "First year of the date range the search is limited to. \
                                        For example 2020 when searching for records published until 2020. \
                                        Use negative numbers for years before the Common Era, for example -1000 for 1000BCE."
                    },
                    "language": {
                        "type": "string",
                        "description": "ISO 639-3 code for language of the records being searched. For example 'fin' for Finnish or 'deu' for German"
                    }
                },
                "required": ["search_term", "search_type"],
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
                search_type=function_args.get("search_type"),
                formats=function_args.get("formats"),
                year_from=function_args.get("year_from"),
                year_to=function_args.get("year_to"),
                language=function_args.get("language")
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
        bot_response = {}
        try:
            bot_response = predict(message, chat_history)
        except OpenAIError as e:
            print(e)
            bot_response["message"] = "An error occured during execution:\n" + str(e)
            bot_response["chat_history"] = [initial_chat_history]

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