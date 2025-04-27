from flask import Flask, render_template

app = Flask(__name__)

# Home page
@app.route('/')
def home():
    return render_template('index.html')

# Training page
@app.route('/training')
def training():
    return render_template('training.html')

if __name__ == '__main__':
    app.run(debug=True)
