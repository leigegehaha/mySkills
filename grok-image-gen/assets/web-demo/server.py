#!/usr/bin/env python3
import cgi
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.request import Request, urlopen

BASE = Path(__file__).resolve().parent
ENV_PATH = BASE / '.env'
INDEX_PATH = BASE / 'index.html'
API_BASE = 'https://api.vectorengine.ai'


def load_env():
    values = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            values[key.strip()] = value.strip()
    return values


class Handler(BaseHTTPRequestHandler):
    def _send(self, code=200, content_type='text/plain; charset=utf-8', body=b''):
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(204)

    def do_GET(self):
        if self.path in ('/', '/index.html'):
            self._send(200, 'text/html; charset=utf-8', INDEX_PATH.read_bytes())
            return
        if self.path == '/env':
            env = load_env()
            payload = json.dumps({'apiKey': env.get('GROK_IMAGE_API_KEY', '')}).encode('utf-8')
            self._send(200, 'application/json; charset=utf-8', payload)
            return
        self._send(404, body=b'Not Found')

    def do_POST(self):
        env = load_env()
        api_key = env.get('GROK_IMAGE_API_KEY', '')
        if not api_key:
            self._send(500, 'application/json; charset=utf-8', json.dumps({'error': 'Missing GROK_IMAGE_API_KEY in .env'}).encode('utf-8'))
            return

        if self.path == '/proxy/generate':
            length = int(self.headers.get('Content-Length', '0'))
            body = self.rfile.read(length)
            req = Request(
                f'{API_BASE}/v1/images/generations',
                data=body,
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json'
                },
                method='POST'
            )
            try:
                with urlopen(req, timeout=300) as resp:
                    self._send(resp.status, 'application/json; charset=utf-8', resp.read())
            except Exception as e:
                self._send(500, 'application/json; charset=utf-8', json.dumps({'error': str(e)}).encode('utf-8'))
            return

        if self.path == '/proxy/edit':
            form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={'REQUEST_METHOD': 'POST'})
            boundary = '----OpenClawFormBoundary'
            parts = []
            for key in ['prompt', 'model', 'n', 'size']:
                value = form.getvalue(key, '')
                parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode('utf-8'))
            if 'image' in form:
                image_item = form['image']
                filename = image_item.filename or 'image.png'
                content = image_item.file.read()
                parts.append(
                    f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{filename}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode('utf-8') + content + b'\r\n'
                )
            parts.append(f'--{boundary}--\r\n'.encode('utf-8'))
            body = b''.join(parts)
            req = Request(
                f'{API_BASE}/v1/images/edits',
                data=body,
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Accept': 'application/json',
                    'Content-Type': f'multipart/form-data; boundary={boundary}'
                },
                method='POST'
            )
            try:
                with urlopen(req, timeout=300) as resp:
                    self._send(resp.status, 'application/json; charset=utf-8', resp.read())
            except Exception as e:
                self._send(500, 'application/json; charset=utf-8', json.dumps({'error': str(e)}).encode('utf-8'))
            return

        self._send(404, body=b'Not Found')


if __name__ == '__main__':
    server = HTTPServer(('127.0.0.1', 8765), Handler)
    print('Serving on http://127.0.0.1:8765')
    server.serve_forever()
