import numpy as np
import matplotlib.pyplot as plt

# Generate data
x = np.linspace(0, 10, 100)  # 100 points between 0 and 10
y = np.sin(x)  # Sine wave

# Create the plot
plt.figure(figsize=(6, 4))
plt.plot(x, y, label="Sine Wave", color="blue")
plt.xlabel("X-axis")
plt.ylabel("Y-axis")
plt.title("Sine Wave Test Plot")
plt.legend()
plt.grid(True)

# Save the figure
plt.savefig("test_plot.png", dpi=300)

print("Plot saved as test_plot.png")
