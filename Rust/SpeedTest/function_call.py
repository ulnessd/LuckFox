import time

def quad_res(n, m):
    if m <= 0:
        return 0 # Modulus must be positive

    n_to_check = (n % m + m) % m 

    for i in range(m): # Check i from 0 to m-1
        if (i * i) % m == n_to_check:
            return 1 # Found a square, so n is a quadratic residue
    return 0 # No such i found

def main():
    print("Starting Python function call test (Quadratic Residues)")

    start_time = time.perf_counter() # High-resolution timer

    m = 5000  # Modulus
    number_of_QR = 0

    # Test numbers 'n_val' from 0 up to m-1
    for n_val in range(m): 
        number_of_QR += quad_res(n_val, m)

    end_time = time.perf_counter()
    
    duration_s = end_time - start_time
    duration_ms = duration_s * 1000

    print("Function call test complete.")
    print(f"Number of Quadratic Residues found (incl. 0): {number_of_QR}") # Should be 159 for m=1000
    print(f"Time taken: {duration_ms:.3f} ms")


if __name__ == "__main__":
    main()


