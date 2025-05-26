#include <stdio.h>
#include <stdlib.h> // For rand(), srand(), RAND_MAX
#include <time.h>   // For time() to seed srand() and for clock_gettime()

// For CLOCK_MONOTONIC if available
#ifndef CLOCK_MONOTONIC
#define CLOCK_MONOTONIC 1 // Fallback for some systems, though POSIX standard
#endif

int main() {
    printf("Starting C Monte Carlo Pi test\n");

    long long iterations = 10000000; // 10 million iterations
    long long points_inside_circle = 0;
    double x, y;
    double mc_pi;

    // Seed the random number generator
    // It's good practice to seed only once
    srand((unsigned int)time(NULL));

    struct timespec start_ts, end_ts;
    clock_gettime(CLOCK_MONOTONIC, &start_ts); // Start timer

    for (long long i = 0; i < iterations; i++) {
        // Generate random x, y between 0.0 and 1.0
        // rand() returns int between 0 and RAND_MAX
        x = (double)rand() / RAND_MAX;
        y = (double)rand() / RAND_MAX;

        if ((x * x) + (y * y) <= 1.0) {
            points_inside_circle++;
        }
    }

    clock_gettime(CLOCK_MONOTONIC, &end_ts); // Stop timer

    if (iterations > 0) {
        mc_pi = 4.0 * (double)points_inside_circle / (double)iterations;
    } else {
        mc_pi = 0.0;
    }

    long long duration_ns = (end_ts.tv_sec - start_ts.tv_sec) * 1000000000LL + (end_ts.tv_nsec - start_ts.tv_nsec);
    double duration_ms = duration_ns / 1000000.0;
    double duration_us = duration_ns / 1000.0;

    printf("Monte Carlo Pi test complete.\n");
    printf("Calculated Pi \u03C0 \u2248 %.6f\n", mc_pi); // \u03C0 is π, \u2248 is ≈
    printf("Time taken: %.3f ms\n", duration_ms);

    return 0;
}


