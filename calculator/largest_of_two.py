def find_largest(num1, num2):
    """Return the largest of two numbers."""
    if num1 > num2:
        return num1
    else:
        return num2


if __name__ == "__main__":
    # Example usage
    a = 10
    b = 25
    
    largest = find_largest(a, b)
    print(f"The largest of {a} and {b} is: {largest}")
    
    # You can also get input from user
    # a = float(input("Enter first number: "))
    # b = float(input("Enter second number: "))
    # print(f"The largest is: {find_largest(a, b)}")