"""Normalize explicit final MCQ answers without looking at gold or reasoning."""
import argparse
import hashlib
import json
import re
from pathlib import Path

PARSER_VERSION = 'explicit-final-choice-v2'


def extract_final_choice(final):
    text = final.strip()
    # Formatting tolerance, not arbitrary extraction from explanatory prose.
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'\\boxed\{([ABCD])\}', r'\1', text)
    text = re.sub(r'\(([ABCD])\)|（([ABCD])）', lambda m: m[1] or m[2], text, flags=re.IGNORECASE)
    pattern = (
        r'(?:(?:(?:最终|正确)?答案)\s*(?:是|为)?\s*[:：]?\s*'
        r'|(?:我)?(?:选择|选)\s*[:：]?\s*'
        r'|(?:final\s+)?answer\s*(?:is\s*)?[:：]?\s*)?'
        r'(?:选项\s*)?([ABCD])\s*[。.!！]?(?:\s*)'
    )
    match = re.fullmatch(pattern, text, flags=re.IGNORECASE)
    return match[1].upper() if match else None


def normalize(record):
    result = dict(record)
    result['original_parse'] = {key: record.get(key) for key in ['status', 'index', 'choice_letter', 'parse_error']}
    result['parser_version'] = PARSER_VERSION
    # These are complete, non-truncated final segments extracted by the native
    # mode-aware runner. Never rescue a missing think-end or a truncated output.
    if record.get('status') == 'ok' or record.get('parse_error') == 'invalid_final_format':
        letter = extract_final_choice(record.get('final_answer', ''))
        if letter is not None:
            result.update(status='ok', index=ord(letter) - 65, choice_letter=letter, parse_error=None)
    result['parse_changed'] = any(result.get(k) != record.get(k) for k in ['status', 'index', 'choice_letter', 'parse_error'])
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--audit', type=Path, required=True)
    args = ap.parse_args()
    assert not args.output.exists() and not args.audit.exists()
    raw = args.input.read_bytes()
    rows = [json.loads(line) for line in raw.decode().splitlines() if line.strip()]
    assert len({r['question_id'] for r in rows}) == len(rows)
    normalized = [normalize(r) for r in rows]
    args.output.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in normalized))
    audit = dict(parser_version=PARSER_VERSION, input_sha256=hashlib.sha256(raw).hexdigest(),
                 output_sha256=hashlib.sha256(args.output.read_bytes()).hexdigest(),
                 code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 records=len(rows), changed=[r['question_id'] for r in normalized if r['parse_changed']],
                 reason='User explicitly requested treating 答案是 B as B; deterministic final-format tolerance only; raw generations unchanged.')
    args.audit.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
