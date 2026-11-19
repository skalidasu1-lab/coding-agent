import json
from collections.abc import Callable

from functions.get_files_info import get_files_info, schema_get_files_info
from functions.get_file_content import get_file_content, schema_get_file_content
from functions.run_python_file import run_python_file, schema_run_python_file
from functions.write_file import write_file, schema_write_file
from functions.run_c_file import run_c_file, schema_run_c_file
from functions.edit_file import edit_file, schema_edit_file

available_functions = [
    schema_get_files_info,
    schema_get_file_content,
    schema_run_python_file,
    schema_write_file,
    schema_run_c_file,
    schema_edit_file,
]

function_map: dict[str, Callable[..., str]] = {
    "get_files_info": get_files_info,
    "get_file_content": get_file_content,
    "run_python_file": run_python_file,
    "write_file": write_file,
    "run_c_file": run_c_file,
    "edit_file": edit_file,
}


# def call_function(tool_call, verbose: bool = False) -> dict:
def call_function(tool_call, working_directory: str = "./calculator", verbose: bool = False) -> dict:
    function_name = tool_call.function.name

    def error(message: str) -> dict:
        return {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": f"Error: {message}",
        }

    try:
        function_args = json.loads(tool_call.function.arguments or "{}")
    except json.JSONDecodeError as e:
        return error(f"invalid JSON in function arguments: {e}. Use double quotes in valid JSON.")

    if not isinstance(function_args, dict):
        return error("function arguments must be a JSON object")

    if verbose:
        print(f" - Calling function: {function_name}({function_args})")
    else:
        print(f" - Calling function: {function_name}")

    if function_name not in function_map:
        return error(f"Unknown function: {function_name}")

    function_args["working_directory"] = working_directory

    try:
        result = function_map[function_name](**function_args)
    except Exception as e:
        return error(f"calling {function_name} failed: {e}")

    return {
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": result,
    }