#!/usr/bin/env python3
"""Exercise gateway routing; optionally upload a real PDF and run both CV models.

Matching (services/cvmatch-ai): CV da dong bo, "Phu hop voi toi" (Luong D) co muc khop + giai thich khong diem, ung vien
nop don -> recruiter xep hang (Luong C) + giai thich HR. --no-matching bo qua (stack khong bat profile match).
Khong co --cv thi dung CV da co cua ung vien demo.
"""
import argparse
import json
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://localhost:8080')
    parser.add_argument('--model-version', default='v4', choices=['v4'])
    parser.add_argument('--cv', type=Path, help='PDF to upload to the demo candidate account (replaces its CV)')
    parser.add_argument('--extraction-url', default='http://localhost:8001')
    parser.add_argument('--cvmatch-url', default='http://localhost:8003')
    parser.add_argument('--no-matching', action='store_true', help='bo qua kiem tra matching (khong bat profile match)')
    parser.add_argument('--skip-interview', action='store_true', help='stack khong chay interview-service')
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
        print('PASS real Qwen is loaded', flush=True)
    if not args.no_matching:
        health = call('GET', args.cvmatch_url.rstrip('/') + '/health')
        if health.get('status') != 'ok' or health.get('db') != 'ok':
            raise RuntimeError(f'cvmatch not healthy: {health}')
        if health.get('encoder', '').startswith('fake-'):
            print('WARN cvmatch dang dung FakeEncoder: diem khong co y nghia chat luong', flush=True)
        print(f'PASS cvmatch {health["versions"]["ontology_version"]} {health["encoder"]} n_cv={health["n_cv"]}',
              flush=True)

    assert call('GET', '/health')['status'] == 'ok'
    auth = call('POST', '/api/auth/login', {'email': 'candidate@hirelens.local', 'password': 'demo1234'})
    token = auth['token']
    assert call('GET', '/api/auth/me', token=token)['id'] == auth['user']['id']
    jobs = call('GET', '/api/jobs')
    assert isinstance(jobs, list)
    assert 'fields' in call('GET', '/api/cvs', token=token)
    if not args.skip_interview:
        session = call('POST', '/api/interviews/sessions', {}, token)
        assert call('GET', f'/api/interviews/sessions/{session["id"]}', token=token)['id'] == session['id']
    print('PASS gateway, identity, recruitment' + ('' if args.skip_interview else ' and interview session') + ' flow',
          flush=True)

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
        print('PASS PDF -> Qwen -> confirm CV', flush=True)
    if not args.no_matching:
        check_cvmatch(call, token)


def check_cvmatch(call, token, wait_s=120):
    """Ung vien -> Luong D + giai thich; nop don job dau -> recruiter Luong C + giai thich HR."""
    deadline = time.time() + wait_s
    while True:                                   # dong bo CV sang cvmatch chay nen sau khi luu (~2 s/CV tren CPU)
        try:
            mine = call('POST', '/api/matching/mine/refresh', token=token)
            break
        except HTTPError as e:
            if e.code != 503 or time.time() > deadline:
                raise RuntimeError(f'refresh: HTTP {e.code} {e.read().decode(errors="replace")}') from None
            time.sleep(3)
    assert mine, 'cvmatch tra danh sach rong: co job PUBLISHED da dong bo chua?'
    top = mine[0]
    assert top['engine'] == 'cvmatch' and top['band'] in ('high', 'mid', 'low') and 0 <= top['overallScore'] <= 1
    expl = call('GET', f'/api/matching/{top["id"]}/explanation', token=token)
    assert expl['audience'] == 'candidate' and expl['score'] is None and expl['text']
    print(f'PASS cvmatch Luong D: {len(mine)} job, top "{top["jobTitle"]}" {top["band"]}; giai thich ung vien',
          flush=True)

    job_id = top['jobId']
    try:
        call('POST', f'/api/applications/jobs/{job_id}', {}, token)
    except HTTPError as e:
        if e.code not in (400, 409):              # da nop don truoc do
            raise
    recruiter = call('POST', '/api/auth/login', {'email': 'recruiter@hirelens.local', 'password': 'demo1234'})['token']
    try:
        ranked = call('POST', f'/api/matching/jobs/{job_id}/refresh', {}, recruiter)
    except HTTPError as e:
        if e.code == 403:
            print(f'SKIP recruiter demo khong so huu job {job_id}', flush=True)
            return
        raise
    assert ranked, 'recruiter khong thay ung vien da nop don'
    hr = call('GET', f'/api/matching/{ranked[0]["id"]}/explanation', token=recruiter)
    assert hr['audience'] == 'hr' and isinstance(hr['score'], int)
    print(f'PASS cvmatch Luong C: {len(ranked)} ung vien cho job {job_id}; giai thich HR {hr["score"]}/100', flush=True)


if __name__ == '__main__': main()
