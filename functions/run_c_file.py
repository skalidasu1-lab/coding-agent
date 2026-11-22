import os
import subprocess


def run_c_file(
    working_directory: str, file_path: str, args: list[str] | None = None
) -> str:
    try:
        working_dir_abs = os.path.realpath(working_directory)
        abs_file_path = os.path.realpath(os.path.join(working_dir_abs, file_path))

        if os.path.commonpath([working_dir_abs, abs_file_path]) != working_dir_abs:
            return f'Error: Cannot execute "{file_path}" as it is outside the permitted working directory'

        if not os.path.isfile(abs_file_path):
            return f'Error: "{file_path}" does not exist or is not a regular file'

        if not file_path.endswith(".c"):
            return f'Error: "{file_path}" is not a C file'

        binary_path = abs_file_path[:-2] + ".out"

        compiled = subprocess.run(
            ["gcc", abs_file_path, "-o", binary_path],
            cwd=working_dir_abs,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if compiled.returncode != 0:
            return f"Compilation failed:\n{compiled.stderr}"

        command = [binary_path]
        if args:
            command.extend(args)

        result = subprocess.run(
            command,
            cwd=working_dir_abs,
            capture_output=True,
            text=True,
            timeout=30,
            env=clean_env(),
            **child_kwargs(),
        )

        output = []
        if result.returncode != 0:
            output.append(f"Process exited with code {result.returncode}")
        if not result.stdout and not result.stderr:
            output.append("No output produced")
        else:
            if result.stdout:
                output.append(f"STDOUT:\n{result.stdout}")
            if result.stderr:
                output.append(f"STDERR:\n{result.stderr}")

        return "\n".join(output)
    except FileNotFoundError:
        return "Error: gcc was not found. Install it with: sudo apt install build-essential"
    except Exception as e:
        return f"Error: executing C file: {e}"


schema_run_c_file = {
    "type": "function",
    "function": {
        "name": "run_c_file",
        "description": "Compiles a C file with gcc and runs the program, relative to the working directory. Returns compiler errors or the program's output",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path of the .c file to compile and run, relative to the working directory",
                },
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of command-line arguments to pass to the program",
                },
            },
            "required": ["file_path"],
        },
    },
}