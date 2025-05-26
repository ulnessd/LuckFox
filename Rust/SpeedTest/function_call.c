#include <stdio.h>
#include <time.h> // For clock_gettime

// For CLOCK_MONOTONIC if available, otherwise adjust as needed
#ifndef CLOCK_MONOTONIC
#define CLOCK_MONOTONIC 1 // Fallback if not defined, common value
#endif

long long quad_res(long long n, long long m) {
    if (m <= 0) {
        return 0;
    }
    // Ensure n is in the range [0, m-1] and positive
    long long n_to_check = (n % m + m) % m;

    for (long long i = 0; i < m; i++) {
        if ((i * i) % m == n_to_check) {
            return 1; // Found a square, so n is a quadratic residue
        }
    }
    return 0; // No such i found
}

int main() {
    printf("Starting C function call test (Quadratic Residues)\n");

    struct timespec start_ts, end_ts;
    clock_gettime(CLOCK_MONOTONIC, &start_ts); // Start timer

    long long m = 5000; // Modulus
    long long number_of_QR = 0;

    // Test numbers 'n_val' from 0 up to m-1
    for (long long n_val = 0; n_val < m; n_val++) {
        number_of_QR += quad_res(n_val, m);
    }

    clock_gettime(CLOCK_MONOTONIC, &end_ts); // Stop timer

    long long duration_ns = (end_ts.tv_sec - start_ts.tv_sec) * 1000000000LL + (end_ts.tv_nsec - start_ts.tv_nsec);
    double duration_ms = duration_ns / 1000000.0;
    double duration_us = duration_ns / 1000.0;


    printf("Function call test complete.\n");
    printf("Number of Quadratic Residues found (incl. 0): %lld\n", number_of_QR);
    printf("Time taken: %.3f ms\n", duration_ms);      // Print ms

    return 0;
}
