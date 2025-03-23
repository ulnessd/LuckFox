import time
import matplotlib.pyplot as plt
from periphery import GPIO

# GPIO Pin Assignments (Adjust as needed)
PINS = {
    "A": GPIO(52, "in"),  # Alcove A
    "B": GPIO(53, "in"),  # Alcove B
    "C": GPIO(56, "in"),  # Alcove C
    "D": GPIO(57, "in")   # Main Room D
}

# Data Storage
visit_counts = {"A": 0, "B": 0, "C": 0, "D": 0}
time_spent = {"A": 0, "B": 0, "C": 0, "D": 0}
entry_times = {"A": None, "B": None, "C": None, "D": None}

def detect_movement():
    """Check which area the mouse is in and track time."""
    global entry_times
    
    for area, pin in PINS.items():
        if pin.read() == 1:  # Mouse enters area
            if entry_times[area] is None:
                entry_times[area] = time.time()  # Log entry time
                visit_counts[area] += 1
        else:  # Mouse leaves area
            if entry_times[area] is not None:
                time_spent[area] += time.time() - entry_times[area]  # Log time spent
                entry_times[area] = None  # Reset entry time



def generate_plots():
    """Generate and save bar charts for visits and time spent."""
    areas = list(visit_counts.keys())

    # Visit Count Bar Chart
    plt.figure(figsize=(8, 4))
    plt.bar(areas, [visit_counts[a] for a in areas], color="blue")
    plt.xlabel("Area")
    plt.ylabel("Visit Count")
    plt.title("Mouse Visit Counts")
    plt.savefig("mouse_visits.png")
    plt.close()

    # Time Spent Bar Chart
    plt.figure(figsize=(8, 4))
    plt.bar(areas, [time_spent[a] for a in areas], color="green")
    plt.xlabel("Area")
    plt.ylabel("Time Spent (s)")
    plt.title("Time Spent in Each Area")
    plt.savefig("mouse_time_spent.png")
    plt.close()

    print("📊 Plots saved as mouse_visits.png & mouse_time_spent.png")

def main():
    """Main loop to track movements."""
    try:
        print("🔍 Tracking mouse movements (Press Ctrl+C to stop)...")
        while True:
            detect_movement()
            time.sleep(0.1)  # Polling interval

    except KeyboardInterrupt:
        print("\n🛑 Experiment ended! Generating reports...")
        generate_plots()

    finally:
        for pin in PINS.values():
            pin.close()

if __name__ == "__main__":
    main()
