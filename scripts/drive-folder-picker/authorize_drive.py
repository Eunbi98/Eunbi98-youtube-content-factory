"""Desktop OAuth and Google Picker. Credentials stay on the user's machine."""
import json
import os
import re
import secrets
import sys
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import requests
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPE = 'https://www.googleapis.com/auth/drive.file'
TARGET = '1jw6LWt911brvCq6oNBJOZJHW1ZNV1pIO'
BASE = Path(__file__).resolve().parent


def check_folder(token, folder_id, get=requests.get):
    if not re.fullmatch(r'[A-Za-z0-9_-]{10,200}', folder_id):
        raise ValueError('폴더 ID 형식이 올바르지 않습니다.')
    r = get('https://www.googleapis.com/drive/v3/files/' + folder_id,
            params={'fields': 'id,name,mimeType,capabilities(canAddChildren)',
                    'supportsAllDrives': 'true'},
            headers={'Authorization': 'Bearer ' + token}, timeout=(10, 45))
    if r.status_code != 200:
        raise ValueError('폴더 접근 확인 실패 (HTTP %s). 폴더 소유 계정과 선택한 폴더를 확인하세요.' % r.status_code)
    data = r.json()
    if data.get('mimeType') != 'application/vnd.google-apps.folder':
        raise ValueError('파일 대신 폴더를 선택하세요.')
    if not data.get('capabilities', {}).get('canAddChildren'):
        raise ValueError('선택한 폴더에 파일을 추가할 권한이 없습니다.')
    return {'id': data['id'], 'name': data['name']}


def make_handler(token, api_key, app_id, nonce, result):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # URL capability and Google responses never go to logs.

        def reply(self, code, body, content_type='application/json; charset=utf-8'):
            raw = body.encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.end_headers()
            self.wfile.write(raw)

        def valid_host(self):
            return self.headers.get('Host') == '127.0.0.1:' + str(self.server.server_port)

        def do_GET(self):
            if not self.valid_host():
                return self.reply(403, '{}')
            if self.path == '/' + nonce + '/':
                return self.reply(200, (BASE / 'picker.html').read_text(encoding='utf-8'), 'text/html; charset=utf-8')
            if self.path == '/' + nonce + '/config':
                return self.reply(200, json.dumps({'token': token, 'apiKey': api_key, 'appId': app_id, 'target': TARGET}))
            self.reply(404, '{}')

        def do_POST(self):
            origin = 'http://127.0.0.1:' + str(self.server.server_port)
            if not self.valid_host() or self.path != '/' + nonce + '/selection' or self.headers.get('Origin') != origin:
                return self.reply(403, '{}')
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length < 4096:
                    return self.reply(400, '{}')
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError('잘못된 요청입니다.')
                folder_id = data.get('id', '')
                if folder_id != TARGET:
                    raise ValueError('지정한 완성본 폴더(Tictoc)를 선택해 주세요.')
                folder = check_folder(token, folder_id)
                result['folder'] = folder
                self.reply(200, json.dumps({'ok': True, 'name': folder['name']}, ensure_ascii=False))
            except (ValueError, TypeError):
                self.reply(400, json.dumps({'ok': False, 'message': '폴더 확인 실패. 지정한 Tictoc 폴더와 파일 추가 권한을 확인한 뒤 다시 선택하세요.'}, ensure_ascii=False))
            except requests.RequestException:
                self.reply(502, json.dumps({'ok': False, 'message': 'Google API 연결 실패. 인터넷 연결을 확인하고 다시 선택하세요.'}, ensure_ascii=False))
    return Handler


def main():
    print('드라이브 전용 인증 및 완성본 폴더 선택입니다. YouTube 토큰은 변경하지 않습니다.')
    import tkinter as tk
    from tkinter import filedialog, simpledialog
    root = tk.Tk(); root.withdraw()
    path = filedialog.askopenfilename(title='Google Cloud에서 받은 데스크톱 OAuth 클라이언트 JSON 선택', filetypes=[('JSON', '*.json')])
    if not path:
        return
    config = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if 'installed' not in config:
        raise ValueError('데스크톱 앱용 OAuth 클라이언트 JSON을 선택하세요. 토큰 JSON이 아닙니다.')
    api_key = simpledialog.askstring('Google Picker API', '같은 Cloud 프로젝트의 API 키를 입력하세요:', parent=root)
    app_id = simpledialog.askstring('프로젝트 번호', '프로젝트 ID가 아닌 숫자로 된 프로젝트 번호를 입력하세요:', parent=root)
    if not api_key or not app_id or not app_id.strip().isdigit():
        raise ValueError('API 키와 숫자 프로젝트 번호가 필요합니다.')
    api_key = api_key.strip(); app_id = app_id.strip(); root.destroy()
    flow = InstalledAppFlow.from_client_config(config, [SCOPE])
    print('브라우저에서 드라이브 폴더 소유 계정으로 로그인하고 Drive 접근을 허용하세요.')
    creds = flow.run_local_server(host='127.0.0.1', port=0, open_browser=True,
        timeout_seconds=1800, access_type='offline', prompt='consent',
        authorization_prompt_message='브라우저에서 인증을 진행해 주세요. 인증 URL은 공유하지 마세요.',
        success_message='인증 완료. 이 창을 닫고 새로 열리는 폴더 선택 창으로 이동하세요.')
    if not creds.refresh_token:
        raise ValueError('리프레시 토큰이 발급되지 않았습니다. 동의 화면에서 접근을 허용한 뒤 다시 인증하세요.')
    nonce = secrets.token_urlsafe(32); result = {}
    server = HTTPServer(('127.0.0.1', 0), make_handler(creds.token, api_key, app_id, nonce, result))
    server.timeout = 1
    url = 'http://127.0.0.1:' + str(server.server_port) + '/' + nonce + '/'
    print('폴더 선택 창에서 Tictoc 폴더를 선택하세요. 이 실행 창은 닫지 마세요.')
    webbrowser.open(url)
    deadline = time.monotonic() + 1800
    try:
        while 'folder' not in result and time.monotonic() < deadline:
            server.handle_request()
    finally:
        server.server_close()
    if 'folder' not in result:
        raise ValueError('폴더 선택 시간이 만료되었습니다. 다시 실행해 주세요.')
    output = Path.home() / 'Codex-Drive-Auth' / time.strftime('%Y%m%d-%H%M%S')
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    def private_file(name, text):
        fd = os.open(output / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(text)
    private_file('GOOGLE_DRIVE_REFRESH_TOKEN.txt', creds.refresh_token)
    private_file('selected_folder.json', json.dumps(result['folder'], ensure_ascii=False, indent=2))
    print('성공: 폴더 선택 및 파일 추가 권한을 확인했습니다.')
    print('새 GOOGLE_DRIVE_REFRESH_TOKEN.txt 값을 같은 이름의 클라우드 시크릿에 교체하고 게시하세요.')
    print('기존 YOUTUBE_REFRESH_TOKEN은 수정하지 마세요. 인증 결과 파일은 채팅에 첨부하지 마세요.')
    print('저장 위치:', output)
    if os.name == 'nt':
        os.startfile(output)


if __name__ == '__main__':
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print('취소되었습니다. 기존 인증은 유지됩니다.'); sys.exit(1)
    except Exception:
        print('완료하지 못했습니다. API 활성화, 같은 프로젝트의 API 키/프로젝트 번호, OAuth JSON 및 테스트 사용자를 확인하세요.')
        print('오류의 인증 URL, 토큰, JSON 내용은 공유하지 마세요.'); sys.exit(1)
