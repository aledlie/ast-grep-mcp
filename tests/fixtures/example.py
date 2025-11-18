from typing import Any


def hello() -> None:
    print("Hello, World!")


def add(a: Any, b: Any) -> Any:
    return a + b


class Calculator:
    def multiply(self, x: Any, y: Any) -> Any:
        return x * y
