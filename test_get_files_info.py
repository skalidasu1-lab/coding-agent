from functions.get_files_info import get_files_info


def show(label, directory):
    print(f"Result for {label}:")
    result = get_files_info("calculator", directory)
    prefix = "    " if result.startswith("Error:") else "  "
    for line in result.split("\n"):
        print(prefix + line)
    print()


show("current directory", ".")
show("'pkg' directory", "pkg")
show("'/bin' directory", "/bin")
show("'../' directory", "../")