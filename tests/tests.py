import os
import json
import unittest

from openai import AzureOpenAI

client = AzureOpenAI(
  azure_endpoint = "https://finna-ai-test.openai.azure.com/",
  api_key=os.getenv("AZURE_OPENAI_KEY"),
  api_version="2024-02-15-preview"
)

tools = {}
with open("prompts/tools.json", "r") as f:
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
        with open("prompts/system_prompt.md", "r") as f:
            cls.system_prompt = [
                {
                    "role": "system",
                    "content": f.read()
                }
            ]

        # Load test prompts from JSON file
        with open("tests/test_prompts.json", "r") as f:
            cls.test_prompts = json.load(f)

    def _run_test(self, test_cases, test_name):
        """
        Helper method to run a series of test cases.
        """
        for test_case in test_cases:
            with self.subTest(test_case=test_case):
                content = test_case["content"]
                expected_parameters = test_case["parameters"]

                # Generate response
                actual_parameters = generate_response(self.system_prompt + [{"role": "user", "content": content}])

                # Normalize expected search terms
                for term in expected_parameters["search_terms"]:
                    term["search_term"] = term["search_term"].lower()  # Convert search terms to lower case

                # Normalize actual search terms
                for term in actual_parameters["search_terms"]:
                    term["search_term"] = term["search_term"].lower()  # Convert search terms to lower case
                    #term["search_term"] = re.sub(r"[^\w\s]", "", term["search_term"])  # Remove non-alphanumeric characters

                # Convert organizations to lower case
                if actual_parameters.get("organizations"):
                    actual_parameters["organizations"] = [o.lower() for o in actual_parameters["organizations"]]

                # Assert results
                self.assertEqual(actual_parameters, expected_parameters, f"{test_name} failed for prompt: '{content}'.\nexpected:{expected_parameters}\nactual:{actual_parameters}")

    def test_generate_response_errors(self):
       self._run_test(self.test_prompts.get("errors"), "Error test")

    def test_generate_response_art_and_design(self):
       self._run_test(self.test_prompts.get("art_and_design"), "Art and design test")

    def test_generate_response_journalist(self):
        self._run_test(self.test_prompts.get("journalist"), "Journalist test")

    def test_generate_response_student(self):
        self._run_test(self.test_prompts.get("student"), "Student test")

if __name__ == "__main__":
    unittest.main()
