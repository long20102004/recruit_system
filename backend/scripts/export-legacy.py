#!/usr/bin/env python3
"""Read legacy MySQL and export one transaction per destination service (no source writes)."""
import argparse
import json
import re
import shlex
import subprocess
from decimal import Decimal
from pathlib import Path

DOMAINS = {
    'identity': ['users'],
    'recruitment': ['companies', 'candidate_profiles', 'recruiter_profiles', 'skills', 'jobs',
        'job_skills', 'job_applications', 'matching_results', 'setting', 'cv_data'],
    'interview': ['interview_questions', 'evaluation_rubrics', 'model_versions', 'interview_sessions',
        'interview_session_questions', 'interview_responses', 'evaluation_results'],
}

def literal(value):
    if value is None: return 'NULL'
    if isinstance(value, bool): return str(int(value))
    if isinstance(value, (int, float, Decimal)): return str(value)
    if isinstance(value, (dict, list)): value = json.dumps(value, ensure_ascii=False, separators=(',', ':'))
    # Hex avoids SQL escaping, SQL modes, multiline text and command injection.
    return "CONVERT(X'" + str(value).encode('utf-8').hex() + "' USING utf8mb4)"

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default='recruit_system')
    parser.add_argument('--mysql-command', default='mysql -uroot', help='mysql CLI prefix; prefer --defaults-extra-file for credentials')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_]+', args.source): parser.error('invalid source database')
    prefix = shlex.split(args.mysql_command)
    def query(sql):
        result = subprocess.run(prefix + ['--batch', '--raw', '--skip-column-names', '-e', sql],
            check=True, capture_output=True, text=True)
        return [line for line in result.stdout.splitlines() if line]
    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=True)
    for domain, tables in DOMAINS.items():
        statements = ['-- Destination data is replaced; review and back up before importing.', 'START TRANSACTION;']
        statements.extend(f'DELETE FROM `{table}`;' for table in reversed(tables))
        for table in tables:
            columns = [line.split('\t')[0] for line in query(f'SHOW COLUMNS FROM `{args.source}`.`{table}`')]
            selected = [f't.`{column}`' for column in columns]
            joins = ''
            if table == 'interview_sessions':
                columns.extend(['candidate_user_id', 'job_title'])
                selected.extend(['c.user_id', 'j.title'])
                joins = f' JOIN `{args.source}`.candidate_profiles c ON c.id=t.candidate_id LEFT JOIN `{args.source}`.jobs j ON j.id=t.job_id'
            for line in query(f'SELECT JSON_ARRAY({", ".join(selected)}) FROM `{args.source}`.`{table}` t{joins}'):
                row = json.loads(line, parse_float=Decimal)
                statements.append(f'INSERT INTO `{table}` ({", ".join(f"`{c}`" for c in columns)}) VALUES ({", ".join(literal(v) for v in row)});')
        if domain == 'interview':
            # The legacy import clears seeded rows. Recreate the current practice bank with new IDs
            # after historical questions/sessions have been restored; never renumber old questions.
            seed = Path(__file__).resolve().parents[2] / 'AI/data/interview_bank_v2_seed.sql'
            if seed.exists(): statements.append(seed.read_text(encoding='utf-8'))
        statements.append('COMMIT;')
        target = root / f'{domain}.sql'
        target.write_text('\n'.join(statements) + '\n', encoding='utf-8')
        print(f'{domain}: {target}')

if __name__ == '__main__': main()
