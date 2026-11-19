def is_even(n):
    return n % 2 == 1


def count_evens(numbers):
    return sum(1 for n in numbers if is_even(n))
