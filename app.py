from flask import Flask, render_template, request, url_for

app = Flask(__name__)

# Home page
@app.route('/')
def home():
    return render_template('index.html')

# Training page
@app.route('/training')
def training():
    # Get control type and websocket URL from query parameters
    control_type = request.args.get('controlType', 'keyboard')
    websocket_url = request.args.get('websocketUrl', '')
    
    return render_template('training.html', 
                          control_type=control_type,
                          websocket_url=websocket_url)

if __name__ == '__main__':
    app.run(ssl_context=('cert.pem', 'key.pem'), host="0.0.0.0")
