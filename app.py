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

gpt_model = "gpt-4o-mini"
finna_api_base_url = "https://api.finna.fi/api/v1/"

def read_file(file):
    with open(file, "r") as f:
        output = f.read()
        return output

usage_right_codes = {
    "No restrictions (CC0 or Public Domain)": "0/A Free/",
    "No restrictions, source must be named (CC BY or CC BY-SA)": "0/B BY/",
    "No commercial use (CC BY-NC or CC BY-NC-SA)": "0/C NC/",
    "No edits (CC BY-ND)": "0/D ND/",
    "No commercial use, no edits (CC BY-NC-ND)": "0/E NC-ND/",
    "In copyright": "0/G inC/",
    "Usage right not known": "0/H Unknown/"
}

format_codes = {
    "Book": "0/Book/",
    "eBook": "1/Book/eBook/",
    "Audio book": "1/Book/AudioBook/",
    "Journal": "0/Journal/",
    "Article": "1/Journal/Article/",
    "Archive/Collection": "0/Document/",
    "Archive series": "1/Document/ArchiveSeries/",
    "Image": "0/Image/",
    "Thesis": "0/Thesis/",
    "Sound": "0/Sound/",
    "Physical object": "0/PhysicalObject/",
    "Other text": "0/OtherText/",
    "Letter": "1/OtherText/Letter/",
    "Diary": "1/OtherText/Diary/",
    "Musical score": "0/MusicalScore/",
    "Video": "0/Video/",
    "DVD": "1/Video/DVD/",
    "BluRay": "1/Video/BluRay/",
    "Map": "0/Map/",
    "Work of art": "0/WorkOfArt/",
    "Painting": "1/WorkOfArt/Painting/",
    "Sculpture": "1/WorkOfArt/Sculpture/",
    "Installation": "1/WorkOfArt/Installation/",
    "Game": "0/Game/",
    "Video game": "1/Game/VideoGame/",
    "PlayStation 4": "2/Game/VideoGame/PS4/",
    "Nintendo Switch": "2/Game/VideoGame/Switch/",
    "Xbox One": "2/Game/VideoGame/Xbox One/",
    "PlayStation 3": "2/Game/VideoGame/PS3/",
    "PlayStation 5": "2/Game/VideoGame/PS5/",
    "Xbox 360": "2/Game/VideoGame/Xbox 360/",
    "Nintendo Wii": "2/Game/VideoGame/Wii/",
    "Xbox Series X": "2/Game/VideoGame/Xbox X/",
    "PC games": "2/Game/VideoGame/PC/",
    "Nintendo Wii U": "2/Game/VideoGame/Wii U/",
    "Nintendo 3DS": "2/Game/VideoGame/3DS/",
    "Nintendo DS": "2/Game/VideoGame/DS/",
    "Board game": "1/Game/BoardGame/",
    "Place": "0/Place/",
    "Learning material": "0/LearningMaterial/",
    "AIPA": "0/AIPA/"
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
    if all(x in format_codes for x in formats):
        format_filter = ['~format_ext_str_mv:"' + format_codes[x] + '"' for x in formats] if formats else []
    else:
        format_filter = []

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
    limit = kwargs["limit"] or 50

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

tools = json.loads(read_file("tools.json"))

available_functions = {
    "search_library_records": search_library_records
}

def predict(message, chat_history):
    print("-----")
    print("message:\n", message)

    chat_history.append({"role": "user", "content": message})
    response = client.chat.completions.create(
        model=gpt_model,
        messages=chat_history,
        tools=tools,
        tool_choice="auto",
        parallel_tool_calls=False,
        temperature=0.1,
        max_tokens=800,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        seed=1,
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

            response_data = json.loads(function_response)

            # Extract search parameters form the response and remove them from chat history
            search_parameters = response_data["search_parameters"]
            response_data.pop("search_parameters")

            chat_history.append(
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": json.dumps(response_data),
                }
            )

        second_response = client.chat.completions.create(
            model=gpt_model,
            messages=chat_history,
            temperature=0.1,
            max_tokens=800,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            seed=1,
            stop=None
        )
        chat_history.append(second_response.choices[0].message)

        return {
            "message": second_response.choices[0].message.content,
            "chat_history": chat_history,
            "search_parameters": search_parameters,
            "total_tokens": second_response.usage.total_tokens
        }
    
    return {
        "message": response_message.content,
        "chat_history": chat_history,
        "search_parameters": search_parameters,
        "total_tokens": response.usage.total_tokens
    }

initial_chat_history = {
    "role": "system",
    "content": read_file("system_prompt.md")
}

build_date = read_file("date.txt")

with gr.Blocks(css="custom.css") as app:
    # Session state
    chat_history_var = gr.State([initial_chat_history])
    finna_url_var = gr.State("")

    # UI components
    with gr.Row():
        with gr.Column(scale=1):
            chatbot = gr.Chatbot(height="calc(100vh - 240px)")
            msg = gr.Textbox(info="Tokens used: 0/128,000")
            with gr.Row():
                clear = gr.ClearButton(value="Start a new chat", components=[msg, chatbot])
                btn = gr.Button(value="Submit", variant="primary")
        with gr.Column(scale=2):
            iframe = gr.HTML("<iframe src=\"\"></iframe>")
    build_message = gr.HTML(f"<div id=\"build-date\">App last built: {build_date}</div>")

    # Function to be called on submit
    def respond(message, chat_component_history, chat_history, url):
        bot_response = {}
        try:
            bot_response = predict(message, chat_history)
        except Exception as e:
            print(e)
            bot_response["message"] = "An error occurred during execution:\n" + str(e)
            bot_response["chat_history"] = [initial_chat_history]
            bot_response["total_tokens"] = 0
        
        chat_component_history.append((message, bot_response["message"]))

        if bot_response.get("search_parameters"):
            url = "https://testi-instituutio.finna-pre.fi/tekoaly/Search/Results?" + bot_response['search_parameters']['search_url'].split('?',1)[1]
            parameter_message = f"""
                Parameters used in search:\n 
                - Search terms: {', '.join(['`' + i['search_type'] + ':' + i['search_term'] + '`' for i in bot_response['search_parameters']['search_terms']])}\n
                - Search boolean: `{bot_response['search_parameters']['bool']}`\n
                - Filters: `{bot_response['search_parameters']['filters']}`\n
                - Sort method: `{bot_response['search_parameters']['sort_method']}`\n
                Search results can be seen [here]({url})
            """
            chat_component_history.append((None, parameter_message))

        iframe_str = f"<iframe src=\"{url}\"></iframe>"

        return {
            msg: gr.update(value="", info=f"Tokens used: {bot_response['total_tokens']:,}/128,000"),
            chatbot: chat_component_history,
            iframe: iframe_str,
            chat_history_var: bot_response["chat_history"],
            finna_url_var: url
        }
    
    # Function to be called on clear
    def clear_chat():
        return {
            msg: gr.update(value="", info="Tokens used: 0/128,000"),
            iframe: "<iframe src=\"\"></iframe>",
            chat_history_var: [initial_chat_history],
            finna_url_var: ""
        }

    # Event listeners
    msg.submit(fn=respond, inputs=[msg, chatbot, chat_history_var, finna_url_var], outputs=[msg, chatbot, iframe, chat_history_var, finna_url_var])
    btn.click(fn=respond, inputs=[msg, chatbot, chat_history_var, finna_url_var], outputs=[msg, chatbot, iframe, chat_history_var, finna_url_var])
    clear.click(fn=clear_chat, inputs=[], outputs=[msg, iframe, chat_history_var, finna_url_var])

if __name__ == "__main__":
    app.launch()