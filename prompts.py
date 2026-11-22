from study.design import Policy

system_prompt ="""
You are a helpful AI coding agent working on a Python project in the working directory.

When a user asks a question or makes a request, make a function call plan. You can perform the following operations:

- List files and directories
- Read file contents
- Execute Python files with optional arguments
- Write or overwrite files
- Compile and run C files with optional arguments
- Edit a file by replacing one exact piece of text

Guidelines:
- Explore before changing anything: list the files, then read the relevant ones.
- - To change part of an existing file, use edit_file with a short, exact piece of the current text. Read the file first so the text matches exactly. Use write_file only for new files or complete rewrites.
- After changing code, run the relevant Python file (for example tests.py, or main.py with an argument) to verify the fix.
- Only give your final answer once you have verified the fix, and explain what you changed.
- Never repeat a function call with the same arguments. If you already have the result, use it.
- Once a check confirms the expected result, stop calling functions and reply with a short summary of what you found and changed.
- Never repeat a function call with the same arguments. If you already have the result, use it.
- Once a check confirms the expected result, stop calling functions and reply with a short summary of what you found and changed.

All paths you provide should be relative to the working directory. You do not need to specify the working directory in your function calls as it is automatically injected for security reasons.
"""
STUDY_BASE_PROMPT = """
You are a helpful AI coding agent. You work in a working directory and can list files, read files, write or edit files, and run Python files.

The program the user wants must be written in a file named main.py in the working directory. The user will run it from the command line and pass its inputs as command-line arguments. All paths you provide are relative to the working directory.
""".strip()

POLICY_PROMPTS = {
    Policy.NEVER: "Policy: work independently. If the request leaves details unspecified, make reasonable assumptions yourself and mention them briefly in your final answer. Choose the most common, conventional behavior when you have to decide between options. Do not ask the user any questions. Implement the program, test it by running it, and then give your final answer.",
    Policy.WHEN_UNCLEAR: "Policy: if the request is clear enough to implement, proceed without asking. If it leaves out important details that change how the program should behave, ask the user a short question with the ask_user tool before writing code. Ask only what you need, at most three questions in total. Then implement the program, test it by running it, and give your final answer.",
    Policy.ALWAYS: "Policy: before writing any code, always use the ask_user tool to ask the user at least one short question about the details of what they want, even if the request seems clear. Ask only what you need, at most three questions in total. Then implement the program, test it by running it, and give your final answer.",
}