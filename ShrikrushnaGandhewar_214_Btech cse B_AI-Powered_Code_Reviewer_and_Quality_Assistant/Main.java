import java.util.*;

public class Main {

    public static double calculateAverage(int[] numbers) {
        int total = 0;
        for (int i = 0; i < numbers.length; i++) {
            total = total + numbers[i];
        }

        if (numbers.length == 0) {
            return 0;
        } else {
            return (double) total / numbers.length;
        }
    }

    public static List<Integer> findCommonElements(int[] list1, int[] list2) {
        List<Integer> common = new ArrayList<>();
        for (int i = 0; i < list1.length; i++) {
            for (int j = 0; j < list2.length; j++) {
                if (list1[i] == list2[j]) {
                    common.add(list1[i]);
                }
            }
        }
        return common;
    }

    public static void printStudents(String[] students) {
        for (int i = 0; i < students.length; i++) {
            System.out.println(students[i]);
        }
    }

    public static int factorial(int n) {
        int result = 1;
        int i = 1;
        while (i <= n) {
            result = result * i;
            i = i + 1;
        }
        return result;
    }

    public static List<Integer> removeDuplicates(int[] items) {
        List<Integer> unique = new ArrayList<>();
        for (int i = 0; i < items.length; i++) {
            if (!unique.contains(items[i])) {
                unique.add(items[i]);
            }
        }
        return unique;
    }

    public static String searchName(String[] names, String target) {
        boolean found = false;
        for (int i = 0; i < names.length; i++) {
            if (names[i].equals(target)) {
                found = true;
            }
        }

        if (found == true) {
            return "Found";
        } else {
            return "Not Found";
        }
    }

    public static int sumEvenNumbers(int[] nums) {
        int total = 0;
        for (int i = 0; i < nums.length; i++) {
            if (nums[i] % 2 == 0) {
                total += nums[i];
            }
        }
        return total;
    }

    public static void main(String[] args) {

        int[] data1 = {1, 2, 3, 4, 5};
        int[] data2 = {3, 4, 5, 6, 7};

        System.out.println(calculateAverage(data1));
        System.out.println(findCommonElements(data1, data2));
        printStudents(new String[]{"Rahul", "Amit", "Sneha"});
        System.out.println(factorial(5));
        System.out.println(removeDuplicates(new int[]{1, 2, 2, 3, 4, 4, 5}));
        System.out.println(searchName(new String[]{"Krishna", "Ram", "Shyam"}, "Ram"));
        System.out.println(sumEvenNumbers(data1));
    }
}