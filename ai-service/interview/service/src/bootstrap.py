"""Train a version-matched calibration once, then start API; cache lives on DATA."""
from __future__ import annotations
import fcntl,hashlib,json,os,subprocess,sys
from .io_utils import DATA,OUTPUT

def signature(mode, model):
    h=hashlib.sha256((mode+'|'+model).encode())
    from pathlib import Path
    files=[DATA/'interview_bank_v2.json',DATA/'interview_answers_v2.csv']
    files.extend(Path(__file__).with_name(name) for name in ['features.py','coverage.py','train_calibration.py'])
    for path in files:h.update(path.read_bytes())
    return h.hexdigest()

def prepare():
    mode=os.getenv('HIRELENS_MODE','bertscore')
    model=os.getenv('HIRELENS_BERT_MODEL','bert-base-multilingual-cased')
    if mode not in {'fast','bertscore','finetune'}:raise ValueError('Invalid scoring mode')
    if mode=='finetune':
        from .regressor import model_dir
        path=model_dir()
        if not (path/'config.json').exists():
            raise SystemExit(f'Missing fine-tuned model at {path}. Train with: python -m src.finetune_bert --scenario self')
        return
    OUTPUT.mkdir(parents=True,exist_ok=True)
    with (OUTPUT/'.prepare.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        stamp=OUTPUT/f'{mode}.signature'
        expected=signature(mode,model)
        calibration=OUTPUT/f'calibration_{mode}.json'
        if not calibration.exists() or not stamp.exists() or stamp.read_text()!=expected:
            print(f'Preparing {mode} calibration on synthetic rubric labels; first semantic run downloads a model.',flush=True)
            subprocess.run([sys.executable,'-m','src.train_calibration','--mode',mode,'--model-type',model,
                '--device',os.getenv('HIRELENS_DEVICE','cpu')],check=True)
            # Record provenance and checksum with the actual artifact.
            data=json.loads(calibration.read_text());data['data_signature']=expected
            calibration.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
            stamp.write_text(expected)

if __name__=='__main__':
    prepare()
    os.execvp('uvicorn',['uvicorn','src.api:app','--host','0.0.0.0','--port','8000','--workers','1'])
