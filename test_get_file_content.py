from functions.get_file_content import get_file_content

result = get_file_content("calculator", "lorem.txt")
print(f"lorem.txt length: {len(result)}")
print(f"lorem.txt truncated: {'truncated' in result}")
print()

for path in ["main.py", "pkg/calculator.py", "/bin/cat", "pkg/does_not_exist.py"]:
    print(f"Result for {path}:")
    print(get_file_content("calculator", path))
    print()