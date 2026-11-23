import sys


def find_largest(num1, num2, num3):
    """Return the largest of three numbers."""
    if num1 >= num2 and num1 >= num3:
        return num1
    elif num2 >= num1 and num2 >= num3:
        return num2
    else:
        return num3


if __name__ == "__main__":
    # Get numbers from command line arguments or use example values
    if len(sys.argv) == 4:
        a = float(sys.argv[1])
        b = float(sys.argv[2])
        c = float(sys.argv[3])
    else:
        # Example usage
        a = 10
        b = 25
        c = 15

    largest = find_largest(a, b, c)
    print(f"The largest of {a}, {b}, and {c} is: {largest}")

    # You can also get input from user
    # a = float(input("Enter first number: "))
    # b = float(input("Enter second number: "))
    # c = float(input("Enter third number: "))
    # print(f"The largest is: {find_largest(a, b, c)}")