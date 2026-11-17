#!/usr/bin/env python3
"""Live Module 3 smoke: create a practice session, grade generated answers, verify persisted summary.
Uses the demo candidate and creates a new session. Does not modify old sessions or CVs.
"""
import argparse,json
from pathlib import Path
from urllib.request import Request,urlopen

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--url',default='http://localhost:8080')
p.add_argument('--ai-url',default='http://localhost:8000')
p.add_argument('--mode',choices=['bertscore','fast','finetune'],default='bertscore')
a=p.parse_args()

def call(method,path,body=None,token=None):
    url=path if path.startswith('http') else a.url.rstrip('/')+path
    headers={'Content-Type':'application/json'}
    if token:headers['Authorization']='Bearer '+token
    req=Request(url,method=method,headers=headers,data=json.dumps(body).encode() if body is not None else None)
    with urlopen(req,timeout=240) as response:return json.load(response)

health=call('GET',a.ai_url.rstrip('/')+'/health')
assert health['default_mode']==a.mode
if a.mode=='finetune':
    assert health['model_loaded']
else:
    assert health['calibration_loaded'][a.mode]
    if a.mode=='bertscore':assert health['model_loaded']
token=call('POST','/api/auth/login',{'email':'candidate@hirelens.local','password':'demo1234'})['token']
session=call('POST','/api/interviews/sessions',{'questionCount':3},token)
bank=json.loads((Path(__file__).resolve().parents[2]/'AI/data/interview_bank_v2.json').read_text())
by_text={q['question']:q for q in bank['questions']}
for q in session['questions']:
    sample=by_text[q['questionText']]['reference_answer']
    result=call('POST',f'/api/interviews/sessions/{session["id"]}/responses',{'questionId':q['questionId'],'answerText':sample},token)
    assert 0<=result['predictedScore']<=10
    assert result['scoringMode']==a.mode
    assert len(result['criterionResults'])==3
    if a.mode=='bertscore':assert result['bertscoreF1'] is not None
    print(f'PASS graded question {q["questionId"]}: {result["predictedScore"]}/10, mode={a.mode}',flush=True)
report=call('GET',f'/api/interviews/sessions/{session["id"]}/summary',token=token)
assert report['status']=='COMPLETED' and report['answeredQuestions']==3
assert report['averageScore'] is not None
assert len(report['evaluations'])==3
if a.mode=='bertscore':assert all(item['bertscoreF1'] is not None for item in report['evaluations'])
print(f'PASS completed session {session["id"]}: 3 persisted grades, mean={report["averageScore"]}/10')
