from functions.run_python_file import run_python_file

tests = [
    ("main.py", None),
    ("main.py", ["3 + 5"]),
    ("tests.py", None),
    ("../main.py", None),
    ("nonexistent.py", None),
    ("lorem.txt", None),
]

for path, args in tests:
    label = f'"{path}"' + (f", {args}" if args else "")
    print(f"Result for run_python_file(\"calculator\", {label}):")
    print(run_python_file("calculator", path, args))
    print()