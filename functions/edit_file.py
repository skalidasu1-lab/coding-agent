import os


def edit_file(working_directory: str, file_path: str, old_text: str, new_text: str) -> str:
    try:
        working_dir_abs = os.path.realpath(working_directory)
        target_file = os.path.realpath(os.path.join(working_dir_abs, file_path))

        if os.path.commonpath([working_dir_abs, target_file]) != working_dir_abs:
            return f'Error: Cannot edit "{file_path}" as it is outside the permitted working directory'

        if not os.path.isfile(target_file):
            return f'Error: File not found or is not a regular file: "{file_path}"'

        if not old_text:
            return "Error: old_text must not be empty"

        with open(target_file, "r") as f:
            content = f.read()

        count = content.count(old_text)
        if count == 0:
            return f'Error: old_text was not found in "{file_path}". Read the file again and copy the text exactly.'
        if count > 1:
            return f'Error: old_text appears {count} times in "{file_path}". Include more surrounding text so it matches exactly once.'

        with open(target_file, "w") as f:
            f.write(content.replace(old_text, new_text, 1))

        return f'Successfully edited "{file_path}" (replaced 1 occurrence)'
    except Exception as e:
        return f"Error: {e}"


schema_edit_file = {
    "type": "function",
    "function": {
        "name": "edit_file",
        "description": "Edits an existing file by replacing one exact piece of text with new text. The old text must appear exactly once in the file",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path of the file to edit, relative to the working directory",
                },
                "old_text": {
                    "type": "string",
                    "description": "The exact text to replace. It must match the file exactly and appear only once",
                },
                "new_text": {
                    "type": "string",
                    "description": "The text to put in its place",
                },
            },
            "required": ["file_path", "old_text", "new_text"],
        },
    },
}