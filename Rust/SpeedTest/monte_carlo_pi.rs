use std::time::Instant;
use rand::Rng; // Import the Rng trait

fn main() {
    println!("Starting Monte Carlo Pi test");

    let start_time = Instant::now();

    let mut rng = rand::rng(); // Create a random number generator
    let mut inside = 0;
    let mut num_iter = 0;
    // Generate a random float between 0.0 (inclusive) and 1.0 (exclusive)
    for _ in 0..10000000 {

        let x: f64 = rng.random::<f64>();
        let y: f64 = rng.random::<f64>();
        num_iter +=1;
        if x*x + y*y <= 1.0 {
            inside += 1;
        }

    }
    let mcpi: f64 = 4.0*(inside as f64)/(num_iter as f64);

    let duration = start_time.elapsed();

    println!("Monte Carlo Pi test complete. pi = {}", mcpi);
    println!("Time taken: {} ms",duration.as_millis());


}





