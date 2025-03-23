from smbus2 import SMBus  # Use smbus2 instead of smbus

def main():
    data = [0x01, 0x02]

    try:
        i2c_bus = SMBus(3)  

        print("i2cdetect addr: ", end="")
        for address in range(0x7F):
            try:
                i2c_bus.write_i2c_block_data(address, 0, data)
                print("0x{:02X},".format(address), end="")
            except OSError:
                pass  
        print()

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        if i2c_bus:
            i2c_bus.close()

if __name__ == "__main__":
    main()
