#!/usr/bin/env python3
"""Exercise gateway routing; optionally upload a real PDF and run both CV models."""
import argparse
import json
import uuid
from pathlib import Path
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://localhost:8080')
    parser.add_argument('--model-version', default='v4', choices=['v3', 'v4', 'v5'])
    parser.add_argument('--cv', type=Path, help='PDF to upload to the demo candidate account (replaces its CV)')
    parser.add_argument('--extraction-url', default='http://localhost:8001')
    parser.add_argument('--matching-url', default='http://localhost:8002')
    args = parser.parse_args()
    base = args.url.rstrip('/')

    def call(method, path, body=None, token=None, content_type='application/json'):
        headers = {'Content-Type': content_type}
        if token: headers['Authorization'] = 'Bearer ' + token
        data = body if isinstance(body, bytes) else None if body is None else json.dumps(body).encode()
        url = path if path.startswith(('http://', 'https://')) else base + path
        request = Request(url, method=method, headers=headers, data=data)
        with urlopen(request, timeout=240) as response:
            return json.load(response)

    if args.cv:
        if not args.cv.is_file(): parser.error('PDF does not exist')
        extraction = call('GET', args.extraction_url.rstrip('/') + '/health')
        if extraction.get('engine') != 'llama_cpp' or extraction.get('prompt_version') != args.model_version:
            raise RuntimeError(f'Expected Qwen {args.model_version} running through llama.cpp; inspect extraction health')
        matching = call('GET', args.matching_url.rstrip('/') + '/health')
        if matching.get('embedding_backend') != 'sentence-transformers':
            raise RuntimeError('Real Sentence Transformer is not loaded; hash fallback is not an E2E model test')
        print('PASS real Qwen and Sentence Transformer are loaded', flush=True)

    assert call('GET', '/health')['status'] == 'ok'
    auth = call('POST', '/api/auth/login', {'email': 'candidate@hirelens.local', 'password': 'demo1234'})
    token = auth['token']
    assert call('GET', '/api/auth/me', token=token)['id'] == auth['user']['id']
    jobs = call('GET', '/api/jobs')
    assert isinstance(jobs, list)
    assert 'fields' in call('GET', '/api/cvs', token=token)
    session = call('POST', '/api/interviews/sessions', {}, token)
    assert call('GET', f'/api/interviews/sessions/{session["id"]}', token=token)['id'] == session['id']
    print('PASS gateway, identity, recruitment and interview session flow', flush=True)

    if args.cv:
        if not jobs: raise RuntimeError('Create a published JD before running CV matching')
        boundary = 'hirelens-' + uuid.uuid4().hex
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="e2e-cv.pdf"\r\n'
                'Content-Type: application/pdf\r\n\r\n').encode() + args.cv.read_bytes() + f'\r\n--{boundary}--\r\n'.encode()
        print('Running Qwen extraction; CPU inference may take several minutes...', flush=True)
        cv = call('POST', '/api/cvs', body, token, f'multipart/form-data; boundary={boundary}')
        assert cv['analyzed'] and cv['parsingStatus'] == 'COMPLETED'
        assert any(field.get('values') for field in cv['fields']), 'Extraction returned an empty form'
        call('PUT', '/api/cvs', {'fields': cv['fields']}, token)
        result = call('POST', '/api/matching/run', {'jobId': jobs[0]['id']}, token)
        assert 0 <= result['overallScore'] <= 1
        assert result['modelVersion'] == 'graph-semantic-matcher-locnh-1983b20'
        saved = call('GET', '/api/matching/mine', token=token)
        assert any(item['id'] == result['id'] for item in saved)
        print(f'PASS PDF -> Qwen -> confirm CV -> real matching -> persisted result; score={result["overallScore"]}', flush=True)

if __name__ == '__main__': main()
