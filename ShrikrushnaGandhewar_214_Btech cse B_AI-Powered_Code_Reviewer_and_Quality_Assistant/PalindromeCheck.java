import java.util.Scanner;

public class PalindromeCheck {

/**
 * Checks if a given string is a palindrome.
 * 
 * @param text the input string to check
 * @return true if the string is a palindrome, false otherwise
 */
    public static boolean isPalindrome(String text) {
        if (text == null || text.isEmpty()) {
            return true;
        }

        int left = 0;
        int right = text.length() - 1;

        text = text.replaceAll("[^a-zA-Z0-9]", "");
        text = text.toLowerCase();
        for (int i = 0; i < text.length() / 2; i++) {
            if (text.charAt(i) != text.charAt(text.length() - i - 1)) {
                return false;
            }
        }

        return true;
    }

    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);

        System.out.print("Enter a word: ");
        String word = sc.nextLine();

        if (isPalindrome(word)) {
            System.out.println(word + " is a palindrome");
        } else {
            System.out.println(word + " is not a palindrome");
        }

        sc.close();
    }
}
