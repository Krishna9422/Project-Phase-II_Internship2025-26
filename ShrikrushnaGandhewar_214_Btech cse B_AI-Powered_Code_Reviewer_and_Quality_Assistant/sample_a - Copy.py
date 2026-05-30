"""Sample a.py."""

# sample_a.py

def calculate_average(numbers):
    """Calculate average.

    Args:
        numbers: Description of numbers.

    Returns:
        Description of the return value.
    """
    total = 0
    for n in numbers:
        total += n
    if len(numbers) == 0:
        return 0
    return total / len(numbers)


def add(a: int, b: int) -> int:
    """
    Add two integers and return their sum.

    Args:
        a (int): The first integer to add.
        b (int): The second integer to add.

    Returns:
        int: The sum of `a` and `b`.
    """
   
    return a + b


def find_max(numbers):
    """
    Find the maximum value in a sequence of numbers.

    Args:
        numbers (Sequence[int] | Sequence[float]): A sequence of numeric values to
            evaluate. If the sequence is empty, the function returns ``None``.

    Returns:
        int | float | None: The largest number in ``numbers``. Returns ``None`` when
            ``numbers`` is empty.
    """
    if not numbers:
        return None
    max_num = numbers[0]
    for n in numbers:
        if n > max_num:
            max_num = n
    return max_num


def is_even(n):
    """
    Check if a number is even.

    Args:
        n (int): The integer to evaluate.

    Returns:
        bool: ``True`` if ``n`` is even, otherwise ``False``.
    """
    return n % 2 == 0


