from functions.write_file import write_file

tests = [
    ("lorem.txt", "wait, this isn't lorem ipsum"),
    ("pkg/morelorem.txt", "lorem ipsum dolor sit amet"),
    ("/tmp/temp.txt", "this should not be allowed"),
]

for path, content in tests:
    print(f"Result for {path}:")
    print(write_file("calculator", path, content))
    print()