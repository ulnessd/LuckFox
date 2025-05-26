use std::time::Instant;

fn main() {
    println!("Starting loop test");

    let start_time = Instant::now();

    let mut sum: i64 = 0;
    for i in 1..1000 {
        for j in 1..1000 {
            sum =(sum + i + j)%100000;
        }
    }

    let duration = start_time.elapsed();

    println!("Loop test complete. Final sum: {}", sum);
    println!("Time taken for loops: {} ms",duration.as_millis());

}
