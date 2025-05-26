import time

def main():
    print("Starting loop test")

    start_time = time.perf_counter() # Use perf_counter for more precise timing

    sum_val = 0 # In Python, integers have arbitrary precision, so no need to specify i64 explicitly
                # unless you were to use NumPy arrays of a specific type later.

    # Python's range(start, end) goes up to end-1.
    # Rust's 1..1000 goes from 1 up to (and including) 999.
    # So range(1, 1000) in Python is equivalent.
    for i in range(1, 1000): 
        for j in range(1, 1000):
            sum_val = (sum_val + i + j) % 100000

    end_time = time.perf_counter()
    duration_ns = (end_time - start_time) * 1_000_000_000 # Convert seconds to nanoseconds
    duration_ms = (end_time - start_time) * 1000       # Convert seconds to milliseconds

    print(f"Loop test complete. Final sum: {sum_val}")
    print(f"Time taken for loops: {duration_ns:.0f} ns")
    print(f"Time taken for loops: {duration_ms:.3f} ms")

if __name__ == "__main__":
    main()

