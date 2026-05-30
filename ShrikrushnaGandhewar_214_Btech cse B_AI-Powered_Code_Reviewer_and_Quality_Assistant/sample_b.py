"""Sample b.py."""
def is_palindrome(text):
    """Is palindrome.

    Args:
        text: Description of text.

    Returns:
        Description of the return value.
    """
    reversed_text = ""

    # Reverse the string using a loop
    for i in range(len(text) - 1, -1, -1):
        reversed_text += text[i]

    # Check if original and reversed are same
    return text == reversed_text



word = input("Enter a word: ")

if is_palindrome(word):
    print(word, "is a palindrome")
else:
 print(word, "is not a palindrome")
