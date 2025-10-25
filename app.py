from flask import Flask, render_template, request
from automation import fill_form_and_capture, send_email

app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    return render_template("index.html")

@app.route('/send', methods=['POST'])
def send_assignment():
    try:
        fill_form_and_capture()
        send_email()
        message = "✅ Assignment submitted and email sent successfully!"
    except Exception as e:
        message = f"❌ Error: {e}"

    return render_template("index.html", message=message)

if __name__ == "__main__":
    app.run(debug=True)
