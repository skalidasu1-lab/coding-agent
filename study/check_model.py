import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv  # noqa: E402
from openai import OpenAI  # noqa: E402

from call_function import available_functions  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("--model", required=True)
args = parser.parse_args()

load_dotenv()
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"])
response = client.chat.completions.create(
    model=args.model,
    messages=[{"role": "user", "content": "List the files in the working directory using the available function."}],
    tools=available_functions,
    temperature=0,
)
message = response.choices[0].message
print("served by:", response.model)
print("tool calls:", [(c.function.name, c.function.arguments) for c in message.tool_calls] if message.tool_calls else None)
print("usage:", response.usage)