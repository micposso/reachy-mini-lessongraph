# Python Functions

## What is a Function?

A **function** is a reusable block of code that performs a specific task. Functions help you organize your code, avoid repetition, and make programs easier to read and maintain.

## Defining a Function

Use the `def` keyword to define a function in Python:

```python
def greet():
    print("Hello, World!")

# Call the function
greet()  # Output: Hello, World!
```

## Function Parameters

Functions can accept **parameters** (also called arguments) to receive input:

```python
def greet(name):
    print(f"Hello, {name}!")

greet("Alice")  # Output: Hello, Alice!
greet("Bob")    # Output: Hello, Bob!
```

### Multiple Parameters

```python
def add(a, b):
    return a + b

result = add(3, 5)
print(result)  # Output: 8
```

## Return Values

Use the `return` statement to send a value back from the function:

```python
def square(number):
    return number * number

result = square(4)
print(result)  # Output: 16
```

### Returning Multiple Values

```python
def get_min_max(numbers):
    return min(numbers), max(numbers)

minimum, maximum = get_min_max([1, 5, 3, 9, 2])
print(f"Min: {minimum}, Max: {maximum}")  # Min: 1, Max: 9
```

## Default Parameters

You can provide default values for parameters:

```python
def greet(name, greeting="Hello"):
    print(f"{greeting}, {name}!")

greet("Alice")              # Output: Hello, Alice!
greet("Bob", "Good morning")  # Output: Good morning, Bob!
```

## Keyword Arguments

Call functions using parameter names for clarity:

```python
def describe_pet(name, animal_type, age):
    print(f"{name} is a {age}-year-old {animal_type}")

describe_pet(name="Buddy", animal_type="dog", age=3)
```

## Summary

Functions are essential building blocks in Python that:
- Make code reusable and organized
- Accept parameters for flexible input
- Return values for further processing
- Support default and keyword arguments
