import os
from openai import AzureOpenAI
import gradio as gr
import json
import requests
import pandas as pd
import numpy as np

client = AzureOpenAI(
  azure_endpoint="https://finna-ai-test.openai.azure.com/",
  api_key=os.getenv("AZURE_OPENAI_KEY"),
  api_version="2024-02-15-preview"
)

finna_api_base_url = "https://api.finna.fi/api/v1/"

usage_right_codes = {
    "No restrictions (CC0 or Public Domain)": "0/A Free/",
    "No restrictions, source must be named (CC BY or CC BY-SA)": "0/B BY/",
    "No commercial use (CC BY-NC or CC BY-NC-SA)": "0/C NC/",
    "No edits (CC BY-ND)": "0/D ND/",
    "No commercial use, no edits (CC BY-NC-ND)": "0/E NC-ND/",
    "In copyright": "0/G inC/",
    "Usage right not known": "0/H Unknown/"
}

def get_most_similar_embedding(file, text):
    # Read embeddings from file
    df = pd.read_pickle(file)
    # Get an embedding for the given text
    embedding = client.embeddings.create(input=text, model="text-embedding-ada-002").data[0].embedding
    # Compare embeddings using cosine similarity
    df["similarities"] = df["embedding"].apply(lambda x: np.dot(x, embedding) / (np.linalg.norm(x) * np.linalg.norm(embedding)))
    # Return value of the most similar embedding
    return df.loc[df["similarities"].idxmax(), "value"]

def search_library_records(**kwargs):
    print("search parameters:\n", json.dumps(kwargs, indent=2))

    # Set search terms and types
    search_terms = kwargs["search_terms"]
    lookfor = [t["search_term"] for t in search_terms] if search_terms else None
    types = [t["search_type"] for t in search_terms] if search_terms else None

    # Set search bool
    search_bool = kwargs["search_bool"] or 'AND'

    # Set format filter
    formats = kwargs["formats"]
    if type(formats) != list:
        formats = [formats]
    format_filter = ['~format_ext_str_mv:"0/' + f + '/"' for f in formats] if formats and formats[0] else []

    # Set date range filter
    if kwargs["year_from"] and kwargs["year_to"]:
        date_from = str(kwargs["year_from"]) if kwargs["year_from"] else "*"
        date_to = str(kwargs["year_to"]) if kwargs["year_to"] else "*"
        date_range_filter = ['search_daterange_mv:"[' + date_from + ' TO ' + date_to + ']"']
    else:
        date_range_filter = ''
    
    # Set language filter
    languages = kwargs["languages"]
    if type(languages) != list:
        languages = [languages]
    language_filter = ['~language:"' + l + '"' for l in languages] if languages and languages[0] else []

    # Set building filter
    organizations = kwargs["organizations"]
    if type(organizations) != list:
        organizations = [organizations]
    building_filter = ['~building:"' + get_most_similar_embedding("organizations_embeddings.pkl", o) + '"' for o in organizations] if organizations[0] else []

    # Set hierarchy filter
    journals = kwargs["journals"]
    if type(journals) != list:
        journals = [journals]
    hierarchy_filter = ['~hierarchy_parent_title:"' + get_most_similar_embedding("journals_embeddings.pkl", j) + '"' for j in journals] if journals[0] else []
    
    # Set usage rights filter
    usage_rights = kwargs["usage_rights"]
    if type(usage_rights) != list:
        usage_rights = [usage_rights]
    if all(x in usage_right_codes for x in usage_rights):
        usage_rights = ['~usage_rights_ext_str_mv:"' + usage_right_codes[x] + '"' for x in usage_rights] if usage_rights else []
    else:
        usage_rights = []

    # Set online filter
    online_filter = ['free_online_boolean:"1"'] if kwargs["available_online"] else []
    
    # Set filters
    filters = []
    filters += format_filter
    filters += date_range_filter
    filters += language_filter
    filters += building_filter
    filters += hierarchy_filter
    filters += online_filter
    filters += usage_rights
    print("filters:\n", filters)

    # Set fields to be returned
    fields = kwargs["fields"]
    if type(fields) != list:
        fields = [fields]
    fields += [
        "buildings",
        "formats",
        "id",
        "imageRights",
        "languages",
        "nonPresenterAuthors",
        "presenters",
        "series",
        "subjects",
        "title",
        "urls",
        "year",
    ]

    # Set sort method
    sort_method = kwargs["sort_method"] if kwargs["sort_method"] else "relevance"

    # Set search query language based on prompt language
    prompt_lng = kwargs["prompt_lng"]
    if not prompt_lng in ["fi", "sv", "en-gb"]:
        prompt_lng = "fi"

    # Set limit to 5 if it was not set before
    limit = kwargs["limit"] or 5

    # Make HTTP request to Finna search API
    req = requests.get(
        finna_api_base_url + 'search',
        params={
            "lookfor0[]": lookfor,
            "type0[]": types,
            "bool0[]": search_bool,
            "filter[]": filters,
            "field[]": fields,
            "sort": sort_method,
            "lng": prompt_lng,
            "limit": limit
        }
    )
    req.raise_for_status()
    
    results = req.json()
    results["search_parameters"] = {
        "search_terms": search_terms,
        "bool": search_bool,
        "filters": filters,
        "fields": fields,
        "sort_method": sort_method,
        "limit": limit,
        "search_url": req.url
    }
    
    return json.dumps(results, indent=2)

tools = [
    {
        "type": "function",
        "function": {
            "name": "search_library_records",
            "strict": True,
            "description": "Search a library database for records (i.e. books, movies, etc) and their fields (i.e. authors, title, etc).",
            "parameters": {
                "type": "object",
                "properties": {
                    "search_terms": {
                        "type": "array",
                        "description": "Array of search terms and search types that are used to find information about library records.\
                                        For example, [{\"search_term\": \"Stephen King\", \"search_type\": \"Author\"}, {\"search_term\": \"horror\", \"search_type\": \"Subject\"}]\
                                        when searching for records about horror made by Stephen King.",
                        "items": {
                            "type": "object",
                            "description": "Object containing the search term and its type. ONLY use `search_term` and `search_type` properties in this object.",
                            "properties": {
                                "search_term": {
                                    "type": "string",
                                    "description": "The search term used to find information about the library records. \
                                                    May be a single term, multiple words or a complex query containing boolean operators (AND, OR, NOT), quotes etc. \
                                                    For example, \"cats AND dogs\" when searching for both \"cats\" and \"dogs\" or \"cats NOT dogs\" when \"dogs\" should be excluded.\
                                                    ALWAYS use uppercase boolean operators.",
                                },
                                "search_type": {
                                    "type": "string",
                                    "description": "The type of field being searched. \
                                                    For example, use \"Title\" to match search term to titles of records or \"Subject\" to match search term to subjects of records. \
                                                    ONLY use the options given.",
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
                            }
                        }
                    },
                    "search_bool": {
                        "type": "string",
                        "description": "Boolean operator that connects all of the search terms.\
                                        Use \"AND\" when search results should match all search terms and \"OR\" when search results could match any.\
                                        Only use the options given. ALWAYS use search_bool if there is more than one search term.",
                        "enum": [
                            "AND",
                            "OR"
                        ]
                    },
                    "formats": {
                        "type": "array",
                        "description": "Array of format filters used to limit search results by record type. \
                                        For example, using [\"Book\", \"Image\"] to only search for books and images. \
                                        You can use multiple format filters at once. \
                                        Only use the options given. Leave empty if no formats are specified. When formats is empty, all record types are included in results.",
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
                                        For example, ['fin', 'deu'] when searching for records in Finnish or German. \
                                        Leave empty if no languages are specified.",
                        "items": {
                            "type": "string",
                            "description": "ISO 639-3 code for the language of the records being searched. \
                                            For example 'fin' for Finnish or 'deu' for German. \
                                            Leave empty if no languages are specified."
                        }
                    },
                    "organizations": {
                        "type": "array",
                        "description": "Array of organizations where the records being searched are available. \
                                        For example [\"The National Library\", \"Åbo Akademi Library\"] when the user asks which records are available at the National Library and at Åbo Akademi Library. \
                                        DO NOT guess what the user meant, just use the name given in the prompt. \
                                        You can use multiple organizations at once. Leave empty if no organization is specified in the prompt.",
                        "items": {
                            "type": "string",
                            "description": "The name of the organization whose records are being searched."
                        }
                    },
                    "journals": {
                        "type": "array",
                        "description": "Array of the journals in which the articles being searched have been published. \
                                        For example [\"Helsingin Sanomat\", \"Turun Sanomat\"] when the user is searching for articles published in Helsingin Sanomat and in Turun Sanomat. \
                                        DO NOT guess what the user meant, just use the name given in the prompt. \
                                        You can use multiple journals at once. Leave empty if no journal is specified in the prompt.",
                        "items": {
                            "type": "string",
                            "description": "The name of the journal whose articles are being searched."
                        }
                    },
                    "usage_rights": {
                        "type": "array",
                        "description": "Array of usage right filters used to limit searches to records with certain rights.\
                                        For example, [\"No commercial use (CC BY-NC or CC BY-NC-SA)\", \"No commercial use, no edits (CC BY-NC-ND)\"] when searching for records not available for commercial use.\
                                        You can use multiple restrictions at once. Leave empty if no rights are specified in the prompt.",
                        "items": {
                            "type": "string",
                            "description": "Type of usage right restrictions that records can have.",
                            "enum": [
                                "No restrictions (CC0 or Public Domain)",
                                "No restrictions, source must be named (CC BY or CC BY-SA)",
                                "No commercial use (CC BY-NC or CC BY-NC-SA)",
                                "No edits (CC BY-ND)",
                                "No commercial use, no edits (CC BY-NC-ND)",
                                "In copyright",
                                "Usage right not known"
                            ]
                        }
                    },
                    "fields": {
                        "type": "array",
                        "description": "List of record fields to return in addition to default fields. \
                                        For example, [\"institutions\"] to see the organizations that hold the records or [\"physicalDescriptions\"] to see the number of pages of a book. \
                                        You can specify multiple fields at once. \
                                        Only use the options given. Leave empty if no fields are specified.",
                        "items": {
                            "type": "string",
                            "description": "Field to be returned.",
                            "enum": [
                                "alternativeTitles",
                                "awards",
                                "buildings",
                                "callNumbers",
                                "classifications",
                                "collections",
                                "edition",
                                "genres",
                                "imageRights",
                                "institutions",
                                "isbn",
                                "originalLanguages",
                                "physicalDescriptions",
                                "placesOfPublication",
                                "publishers",
                                "rating",
                                "summary",
                                "toc"
                            ]
                        }
                    },
                    "sort_method": {
                        "type": "string",
                        "description": "The method used to sort search results. \
                                        For example, \"main_date_str desc\" to sort results by year in a descending order. \
                                        Only use the options given.",
                        "enum": [
                            "relevance",
                            "main_date_str desc",
                            "main_date_str asc",
                            "callnumber",
                            "author",
                            "title",
                            "last_indexed desc"
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
                    "available_online": {
                        "type": "boolean",
                        "description": "Boolean that determines whether the search results are available online. \
                                        When set to True, the search will exclusively return records that are available online. \
                                        If set to False, the results will include records both available and unavailable online."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of records to return. Leave empty if no number is specified in user prompt. Default is 5. "
                    },
                },
                "required": ["search_terms", "prompt_lng"],
                "additionalProperties": False
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
                search_terms=function_args.get("search_terms"),
                search_bool=function_args.get("search_bool"),
                formats=function_args.get("formats"),
                year_from=function_args.get("year_from"),
                year_to=function_args.get("year_to"),
                languages=function_args.get("languages"),
                organizations=function_args.get("organizations"),
                journals=function_args.get("journals"),
                usage_rights=function_args.get('usage_rights'),
                fields=function_args.get("fields"),
                sort_method=function_args.get("sort_method"),
                prompt_lng=function_args.get("prompt_lng"),
                limit=function_args.get("limit"),
                available_online=function_args.get("available_online")
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
            parameter_message = f"""Parameters used in search:\n 
                                - Search terms: {', '.join(['`' + i['search_type'] + ':' + i['search_term'] + '`' for i in bot_response['search_parameters']['search_terms']])}\n
                                - Filters: `{bot_response['search_parameters']['filters']}`\n
                                - Sort method: `{bot_response['search_parameters']['sort_method']}`\n
                                Search results can be seen here: https://www.finna.fi/Search/Results?{bot_response['search_parameters']['search_url'].split('?',1)[1]}"""
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