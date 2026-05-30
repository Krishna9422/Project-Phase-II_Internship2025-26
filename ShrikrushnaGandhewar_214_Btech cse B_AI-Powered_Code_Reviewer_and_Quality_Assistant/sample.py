def calculate_sum(numbers):
    total = 0

    for i in range(len(numbers)):
        total = total + numbers[i]

    return total


def calculate_average(numbers):

    total = 0

    for i in range(len(numbers)):
        total = total + numbers[i]

    if len(numbers) == 0:
        return 0

    average = total / len(numbers)

    return average


def find_max(numbers):

    maximum = numbers[0]

    for i in range(len(numbers)):

        if numbers[i] > maximum:
            maximum = numbers[i]

    return maximum


def find_min(numbers):

    minimum = numbers[0]

    for i in range(len(numbers)):

        if numbers[i] < minimum:
            minimum = numbers[i]

    return minimum


numbers = []

count = int(input("Enter total numbers: "))

index = 0

while index < count:

    value = int(input("Enter number: "))

    numbers.append(value)

    index = index + 1


print("Numbers entered:")

for i in range(len(numbers)):

    print(numbers[i])


even = []

odd = []

for i in range(len(numbers)):

    if numbers[i] % 2 == 0:

        even.append(numbers[i])

    else:

        odd.append(numbers[i])


sum_result = calculate_sum(numbers)

average_result = calculate_average(numbers)

max_result = find_max(numbers)

min_result = find_min(numbers)


squares = []

for i in range(len(numbers)):

    squares.append(numbers[i] * numbers[i])


print("Total:", sum_result)

print("Average:", average_result)

print("Maximum:", max_result)

print("Minimum:", min_result)

print("Even:", even)

print("Odd:", odd)

print("Squares:", squares)


duplicate = []

for i in range(len(numbers)):

    count_duplicate = 0

    for j in range(len(numbers)):

        if numbers[i] == numbers[j]:

            count_duplicate += 1

    if count_duplicate > 1:

        duplicate.append(numbers[i])


print("Duplicates:", duplicate)