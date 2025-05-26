#include <stdio.h>
#include <time.h> // For timing

// For CLOCK_MONOTONIC_RAW if available, otherwise CLOCK_MONOTONIC
// #define CLOCK_TYPE CLOCK_MONOTONIC_RAW
#define CLOCK_TYPE CLOCK_MONOTONIC

int main() {
    printf("Starting C loop test\n");

    struct timespec start_ts, end_ts;
    long long sum = 0; // Use long long for a 64-bit integer, similar to Rust's i64

    // Equivalent to Rust's 1..1000 (loops 999 times)
    // Or 1..10000 for your faster Rust test
    int outer_limit = 1000; // Or 10000, or your N_OUTER from Rust
    int inner_limit = 1000; // Or 10000, or your N_INNER from Rust

    clock_gettime(CLOCK_TYPE, &start_ts); // Start timer

    for (long long i = 1; i < outer_limit; i++) {
        for (long long j = 1; j < inner_limit; j++) {
            sum = (sum + i + j) % 100000;
        }
    }

    clock_gettime(CLOCK_TYPE, &end_ts); // Stop timer

    long long duration_ns = (end_ts.tv_sec - start_ts.tv_sec) * 1000000000LL + (end_ts.tv_nsec - start_ts.tv_nsec);
    double duration_ms = duration_ns / 1000000.0;

    printf("Loop test complete. Final sum: %lld\n", sum);
    printf("Time taken for loops: %lld ns\n", duration_ns);
    printf("Time taken for loops: %.3f ms\n", duration_ms);

    return 0;
}

