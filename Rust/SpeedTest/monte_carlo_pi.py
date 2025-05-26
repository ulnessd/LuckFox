import time
import random # Python's built-in random module

def main():
    print("Starting Python Monte Carlo Pi test")

    start_time = time.perf_counter()

    # rng = random.Random() # Creates an instance, not strictly needed for random.random()
    inside = 0
    num_iter = 0 # You are explicitly counting iterations
    
    iterations_to_run = 10000000 # Matching your Rust loop 0..1000

    for _ in range(iterations_to_run): # Loop 'iterations_to_run' times
        x = random.random() # Generates a float uniformly in [0.0, 1.0)
        y = random.random()
        num_iter += 1
        if x*x + y*y <= 1.0:
            inside += 1
    
    # Ensure num_iter is not zero to avoid DivisionByZeroError if iterations_to_run was 0
    if num_iter == 0:
        mcpi = 0.0 
    else:
        mcpi = 4.0 * float(inside) / float(num_iter)

    end_time = time.perf_counter()
    
    duration_s = end_time - start_time
    duration_ms = duration_s * 1000

    print(f"Monte Carlo Pi test complete. pi \u2248 {mcpi:.6f}") # \u2248 is ≈
    print(f"Time taken: {duration_ms:.3f} ms")

if __name__ == "__main__":
    main()








