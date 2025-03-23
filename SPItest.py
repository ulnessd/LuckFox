import spidev

def main():
    tx_buffer = [ord(char) for char in "hello world!"]
    rx_buffer = [0] * len(tx_buffer)

    try:
        spi = spidev.SpiDev()
        spi.open(0, 0)
        spi.max_speed_hz = 1000000  

        rx_buffer = spi.xfer2(tx_buffer[:])
        print("tx_buffer:\n\r", ''.join(map(chr, tx_buffer)))
        print("rx_buffer:\n\r", ''.join(map(chr, rx_buffer)))

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        if spi:
            spi.close()

if __name__ == "__main__":
    main()
