from typing import List

# Collatz sequence for a given number n(odd or even) until it reaches 1. 
def collatz(n: int) -> List[int]:
    result = [n]  # store starting value

    while n != 1:
        if n % 2 == 0:
            n = n // 2
        else:
            n = 3 * n + 1

        result.append(n)  # store every intermediate value

    return result

# Distinct numbers in a list.
def distinct_numbers(numbers: List[int]) -> int:
    return len(set(numbers)) #Set automatically removes duplicates and len returns the number of elements in the set.