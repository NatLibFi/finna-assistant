import os
import json
import re
import unittest
from openai import AzureOpenAI

client = AzureOpenAI(
  azure_endpoint = "https://finna-ai-test.openai.azure.com/",
  api_key=os.getenv("AZURE_OPENAI_KEY"),
  api_version="2024-02-15-preview"
)

tools = {}
with open("tools.json", "r") as f:
    tools = json.load(f)

def generate_response(messages):
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
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
    tool_calls = completion.choices[0].message.tool_calls
    if tool_calls:
        return json.loads(tool_calls[0].function.arguments)
    else:
        return None

class TestChatbotFunctionParameters(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Load system prompt from md file
        with open("system_prompt.md", "r") as f:
            cls.system_prompt = [
                {
                    "role": "system",
                    "content": f.read()
                }
            ]

        # Load test prompts from JSON file
        with open("test_prompts.json", "r") as f:
            cls.test_prompts = json.load(f)

    def test_generate_response(self):
        for test_case in self.test_prompts:
            with self.subTest(test_case=test_case):
                content = test_case["content"]
                expected_parameters = test_case["parameters"]
                
                # Call the generate_response function
                actual_parameters = generate_response(self.system_prompt + [{"role": "user", "content": content}])
                # Normalize search terms
                for term in actual_parameters["search_terms"]:
                    term["search_term"] = term["search_term"].lower() # Convert search terms to lower case
                    term["search_term"] = re.sub(r"[^\w\s]", "", term["search_term"]) # Remove any non-alphanumeric characters (excluding spaces)
                # Convert organizations to lower case
                if actual_parameters.get("organizations"):
                    actual_parameters["organizations"] = [ o.lower() for o in actual_parameters["organizations"] ]
                
                # Assert that the actual parameters match the expected parameters
                self.assertEqual(actual_parameters, expected_parameters, f"Failed for prompt: '{content}'")

if __name__ == "__main__":
    unittest.main()
