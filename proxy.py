# proxy.py
from flask import Flask, request, send_from_directory, Response
import requests, os

app = Flask(__name__, static_folder='frontend/app', static_url_path='/')
UPSTREAM = os.environ.get('LT_UPSTREAM', 'http://localhost:8010')  # 8010
LIVETALKING_UPSTREAM = os.environ.get('LIVETALKING_UPSTREAM', 'http://fastmcp-livetalking-simple:8010')  # LiveTalking 容器

def _relay(resp: requests.Response):
    headers = [('Content-Type', resp.headers.get('Content-Type', 'application/octet-stream'))]
    return Response(resp.content, status=resp.status_code, headers=headers)

@app.route('/app/<path:path>')
def app_files(path):
    return send_from_directory('frontend/app', path)

@app.route('/Livetalking_virtual_interview/<path:path>')
def livetalking_files(path):
    return send_from_directory('Livetalking_virtual_interview', path)

@app.route('/assets/<path:path>')
def asset_files(path):
    return send_from_directory('frontend/assets', path)

@app.route('/')
def index():
    # 檢查是否為純對話模式
    import os
    if os.environ.get('CHAT_ONLY_MODE', 'false').lower() == 'true':
        return send_from_directory('frontend/app', 'interview-chat-only.html')
    return send_from_directory('frontend/app', 'interview.html')

# 代理 8010 dashboard.html
@app.route('/dashboard.html')
def dashboard():
    try:
        r = requests.get(f'{UPSTREAM}/dashboard.html', timeout=30)
        print('GET dashboard.html', r.status_code)
        return _relay(r)
    except requests.RequestException as e:
        print('Dashboard ERROR:', e)
        return ('Dashboard service unavailable', 503)

# 代理 LiveTalking 服務：GET + POST
@app.route('/ltapi/<path:path>', methods=['GET', 'POST'])
def ltapi(path):
    # 優先嘗試 Docker 容器內的 LiveTalking 服務
    url = f'{LIVETALKING_UPSTREAM}/{path}'
    try:
        if request.method == 'GET':
            r = requests.get(url, params=request.args, timeout=120)
            print('GET (LiveTalking)', url, r.status_code)
            return _relay(r)
        else:
            ct = request.headers.get('Content-Type', '')
            data = request.get_data()
            headers = {'Content-Type': ct} if ct else {}
            r = requests.post(url, params=request.args, data=data, headers=headers, timeout=120)
            print('POST (LiveTalking)', url, r.status_code)
            return _relay(r)
    except requests.RequestException as e:
        print('LIVETALKING UPSTREAM ERROR @', url, e)
        
        # 備用：嘗試本地的 LiveTalking 服務
        backup_url = f'{UPSTREAM}/{path}'
        try:
            if request.method == 'GET':
                r = requests.get(backup_url, params=request.args, timeout=120)
                print('GET (Backup)', backup_url, r.status_code)
                return _relay(r)
            else:
                ct = request.headers.get('Content-Type', '')
                data = request.get_data()
                headers = {'Content-Type': ct} if ct else {}
                r = requests.post(backup_url, params=request.args, data=data, headers=headers, timeout=120)
                print('POST (Backup)', backup_url, r.status_code)
                return _relay(r)
        except requests.RequestException as backup_e:
            print('BACKUP UPSTREAM ERROR @', backup_url, backup_e)
            # 檢查是否為連接錯誤（LiveTalking 服務未啟動）
            if 'Connection refused' in str(e) or 'ConnectionError' in str(e):
                print('LiveTalking 服務未啟動 - 返回友善錯誤訊息')
                return ('{"error": "LiveTalking service unavailable", "message": "虛擬人服務未啟動，對話功能仍可正常使用"}', 503, [('Content-Type', 'application/json')])
            return ('Upstream error', 502)

if __name__ == '__main__':
    print('proxy to', UPSTREAM)
    app.run(host='127.0.0.1', port=8080, debug=True)
