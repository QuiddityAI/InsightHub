import math
from typing import Callable


def run_in_batches(items: list, batch_size: int, function: Callable) -> list:
    results = []
    for batch_number in range(math.ceil(len(items) / float(batch_size))):
        partial_results = function(items[batch_number * batch_size : (batch_number + 1) * batch_size])
        results += partial_results
    return results



def test():
    def fun(items):
        print(items)
        return items

    items = list("abcdefghijklmnopq")

    results = run_in_batches(items, 3, fun)
    print(results)


if __name__ == "__main__":
    test()
