from flask import Flask, Response
import matplotlib.pyplot as plt
import numpy as np
import io

app = Flask(__name__)

def generate_plot():
    """Generates a simple plot with fake data."""
    x = np.linspace(0, 10, 100)
    y = np.sin(x) + np.random.normal(0, 0.1, len(x))  # Fake noisy sine wave data

    fig, ax = plt.subplots()
    ax.plot(x, y, label="Fake Data")
    ax.set_title("Generated Data")
    ax.set_xlabel("Time")
    ax.set_ylabel("Value")
    ax.legend()

    # Save to a BytesIO object
    img = io.BytesIO()
    plt.savefig(img, format='png')
    plt.close(fig)
    img.seek(0)
    return img

@app.route("/")
def home():
    return "<h1>LuckFox Flask Server</h1><p>Graph available at <a href='/plot'>/plot</a></p>"

@app.route("/plot")
def plot():
    """Endpoint to serve the generated plot."""
    img = generate_plot()
    return Response(img.getvalue(), mimetype='image/png')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
