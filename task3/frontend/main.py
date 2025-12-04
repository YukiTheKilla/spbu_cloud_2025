from flask import Flask, render_template, request, Response
import requests
import os

app = Flask(__name__)

# Backend URL inside the cluster
BACKEND_URL = "http://music-player-backend-service:8000"

@app.route('/')
def index():
    try:
        resp = requests.get(f"{BACKEND_URL}/current", timeout=3)
        data = resp.json() if resp.ok else {}
    except:
        data = {}
    return render_template('index.html', current=data.get('track'))

@app.route('/api/<path:endpoint>')
def proxy_api(endpoint):
    try:
        resp = requests.request(
            method='GET',
            url=f"{BACKEND_URL}/{endpoint}",
            headers={key: value for (key, value) in request.headers if key != 'Host'},
            stream=True
        )
        return Response(
            resp.iter_content(chunk_size=1024),
            status=resp.status_code,
            content_type=resp.headers.get('content-type'),
            headers=dict(resp.headers)
        )
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/<path:endpoint>', methods=['POST'])
def proxy_api_post(endpoint):
    try:
        resp = requests.post(
            f"{BACKEND_URL}/{endpoint}",
            headers={key: value for (key, value) in request.headers if key != 'Host'}
        )
        return resp.json(), resp.status_code
    except Exception as e:
        return {'error': str(e)}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8040)