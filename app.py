import os
from openai import AzureOpenAI
import gradio as gr
import json
import requests

client = AzureOpenAI(
  azure_endpoint="https://finna-ai-test.openai.azure.com/",
  api_key=os.getenv("AZURE_OPENAI_KEY"),  
  api_version="2024-02-15-preview"
)

finna_api_base_url = "https://api.finna.fi/api/v1/"

def search_library_records(search_term, search_type, formats, year_from, year_to, languages, sort_method, prompt_lng, limit):
    print('search parameters:\n', search_term, search_type, formats, year_from, year_to, languages, sort_method, prompt_lng, limit)

    # Set format filter
    if (type(formats) != list):
        formats = [formats]
    format_filter = ['~format:"0/' + f + '/"' for f in formats] if formats and formats[0] else []

    # Set date range filter
    date_from = str(year_from) if year_from else "*"
    date_to = str(year_to) if year_to else "*"
    date_range_filter = ['search_daterange_mv:"[' + date_from + ' TO ' + date_to + ']"']
    
    # Set language filter
    if (type(languages) != list):
        languages = [languages]
    language_filter = ['~language:"' + l + '"' for l in languages] if languages and languages[0] else []
    
    # Set filters
    filters = []
    filters += format_filter
    filters += date_range_filter
    filters += language_filter
    print("filters:\n", filters)

    # Set sort method
    if not sort_method:
        sort_method = "relevance,id asc"

    # Set search query language based on prompt language
    if not prompt_lng in ["fi", "sv", "en-gb"]:
        prompt_lng = "fi"

    # Set limit
    limit = 10 if not limit else limit

    # Make HTTP request to Finna search API
    req = requests.get(finna_api_base_url + 'search', params={"lookfor0[]": search_term, "type0[]": search_type, "filter[]": filters, "sort": sort_method, "lng": prompt_lng, "limit": limit})
    req.raise_for_status()
    
    results = req.json()
    results["search_parameters"] = {
        "search_term": search_term,
        "search_type": search_type,
        "filters": filters,
        "sort_method": sort_method,
        "search_url": req.url
    }
    
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
                        "description": "The search term used to find information about the library records. \
                                        May be a single term, multiple words or a complex query containing boolean operators (AND, OR, NOT), quotes etc. \
                                        For example \"cats AND dogs\" when searching for both \"cats\" and \"dogs\". Always use uppercase boolean operators.",
                    },
                    "search_type": {
                        "type": "string",
                        "description": "The type of field being searched. \
                                        For example, use \"Title\" to match search term to titles of records or \"Subject\" to match search term to subjects of records. \
                                        Subjects are used to signify what the records are about. \
                                        Only use the options given.",
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
                                        For example, using [\"Book\", \"Image\"] to only search for books and images. \
                                        You can use multiple format filters at once. \
                                        Only use the options given. Leave empty if no formats are specified.",
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
                                "frågelistsvar",
                                "offentliggjord inspelning"
                            ]
                        }
                    },
                    "year_from": {
                        "type": "integer",
                        "description": "First year of the date range the search is limited to. \
                                        For example, 2020 when searching for records published since 2020. \
                                        Use negative numbers for years before the Common Era, for example -1000 for 1000BCE. \
                                        Leave empty if no date range is specified."
                    },
                    "year_to": {
                        "type": "integer",
                        "description": "First year of the date range the search is limited to. \
                                        For example, 2020 when searching for records published until 2020. \
                                        Use negative numbers for years before the Common Era, for example -1000 for 1000BCE. \
                                        Leave empty if no date range is specified."
                    },
                    "languages": {
                        "type": "array",
                        "description": "Array of ISO 639-3 codes for the languages of the records being searched. \
                                        For example, ['fin', 'deu'] for Finnish and German. \
                                        Leave empty if no languages are specified.",
                        "items": {
                            "type": "string",
                            "description": "ISO 639-3 code for the language of the records being searched. \
                                            For example 'fin' for Finnish or 'deu' for German. \
                                            Leave empty if no languages are specified."
                        }
                    },
                    "sort_method": {
                        "type": "string",
                        "description": "The method used to sort search results. \
                                        For example, \"main_date_str desc\" to sort results by year in a descending order. \
                                        Only use the options given.",
                        "enum": [
                            "relevance,id asc",
                            "main_date_str desc",
                            "main_date_str asc",
                            "callnumber",
                            "author",
                            "title",
                            "last_indexed desc,id asc"
                        ]
                    },
                    "prompt_lng": {
                        "type": "string",
                        "description": "Language of the prompt from the user. \"fi\" for Finnish, \"sv\" for Swedish and \"en-gb\" for English. \
                                        If the prompt is not in Finnish, Swedish or English, use Finnish. For example, if the prompt is in German, use \"fi\". Only use the options given.",
                        "enum": [
                            "fi",
                            "sv",
                            "en-gb"
                        ]
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of records to return. Leave empty if no number is specified in user prompt."
                    }
                },
                "required": ["prompt_lng"],
            },
        },
    }
]

available_functions = {
    "search_library_records": search_library_records
}

def predict(message, chat_history):
    print("-----")
    print("message:\n", message)

    chat_history.append({"role": "user", "content": message})
    response = client.chat.completions.create(
        model="gpt-35-turbo-1106",
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

    search_parameters = {}

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
                languages=function_args.get("languages"),
                sort_method=function_args.get("sort_method"),
                prompt_lng=function_args.get("prompt_lng"),
                limit=function_args.get("limit")
            )

            search_parameters = json.loads(function_response)["search_parameters"]

            chat_history.append(
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_response,
                }
            )
        second_response = client.chat.completions.create(
            model="gpt-35-turbo-1106",
            messages=chat_history,
        )
        return {
            "message": second_response.choices[0].message.content,
            "chat_history": chat_history,
            "search_parameters": search_parameters
        }
    
    return {
        "message": response.choices[0].message.content,
        "chat_history": chat_history,
        "search_parameters": search_parameters
    }

def read_system_prompt():
    with open("system_prompt.md", "r") as f:
        output = f.read()
        return output

initial_chat_history = {
    "role": "system",
    "content": read_system_prompt()
}

with gr.Blocks() as app:
    # Session state
    chat_history_var = gr.State([initial_chat_history])

    # UI components
    chatbot = gr.Chatbot(height="calc(100vh - 200px)")
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
        except Exception as e:
            print(e)
            bot_response["message"] = "An error occurred during execution:\n" + str(e)
            bot_response["chat_history"] = [initial_chat_history]
        
        chat_component_history.append((message, bot_response["message"]))

        if bot_response.get("search_parameters"):
            parameter_message = f"Parameters used in search:\n \
                                - Search term: `{bot_response['search_parameters']['search_term']} `\n \
                                - Search type: `{bot_response['search_parameters']['search_type']}`\n \
                                - Filters: `{bot_response['search_parameters']['filters']}`\n \
                                - Sort method: `{bot_response['search_parameters']['sort_method']}`\n\n \
                                Search results can be seen here: https://www.finna.fi/Search/Results?{bot_response['search_parameters']['search_url'].split('?',1)[1]}"
            chat_component_history.append((None, parameter_message))

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