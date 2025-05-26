use std::time::Instant;

fn main() {
    println!("Starting function call test");

    let start_time = Instant::now();

    let m: i64 = 5000;
    let mut number_of_QR: i64 = 0;

    for n in 0..m {
        number_of_QR = number_of_QR + quad_res(n,m);

    }

    let duration = start_time.elapsed();

    println!("Function call test complete. Number of QR: {}", number_of_QR);
    println!("Time taken: {} ms",duration.as_millis());

}

fn quad_res(n: i64, m: i64) -> i64 {
    for i in 0..m {
        if i*i % m == n {
            return 1;
        }
    }
    return 0;
}

