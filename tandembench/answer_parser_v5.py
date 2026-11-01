"""Extract an explicit terminal MCQ answer; never consult gold or earlier reasoning."""
import json
import re
from .normalize_qwen_answers import extract_final_choice

PARSER_VERSION = 'explicit-final-expression-v5-four-options'


def expression(text):
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text.strip())
    text = re.sub(r'`([^`]+)`', r'\1', text)
    old = extract_final_choice(text)
    if old:
        return old
    if text.startswith('{'):
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            return None
        if isinstance(value, dict) and len(value) == 1:
            key, answer = next(iter(value.items()))
            if key in {'answer', 'final_answer', 'choice', '答案', '选项'} and isinstance(answer, str):
                return extract_final_choice(answer)
        return None
    patterns = [
        r'(?:(?:因此|所以|故|综上(?:所述)?)[，,：:]?\s*)?(?:(?:最终|正确)?(?:答案(?:选择|输出)?|选项|选择|输出)|(?:我)?(?:选择|选))\s*(?:应为|应该是|是|为)?\s*[:：]?\s*(?:选项\s*)?([ABCD])\s*[。.!！]?',
        r'(?:(?:therefore|thus|so)[,:]?\s*)?(?:(?:the\s+)?(?:final\s+)?answer(?:\s+selection)?|output|(?:I\s+)?(?:will\s+)?(?:select|choose))\s*(?:is\s*)?[:：]?\s*(?:option\s+)?([ABCD])\s*[.!]?',
    ]
    patterns += [
        r'(?:(?:therefore|thus|so)[,:]?\s*)?(?:option\s+)?([ABCD])\s+is\s+(?:the\s+)?(?:correct(?:\s+(?:one|answer|choice|option))?|best(?:\s+(?:answer|choice|option))?|optimal(?:\s+(?:choice|option))?)\s*[.!]?',
        r'(?:(?:因此|所以|故)[，,]?\s*)?(?:选项|方案)?([ABCD])\s*(?:是|为)(?:正确(?:答案|选项|选择)?|最优(?:解|方案|选项)?|最佳(?:选择|选项|方案))\s*[。.!！]?',
    ]
    for pattern in patterns:
        match = re.fullmatch(pattern, text, flags=re.IGNORECASE)
        if match:
            return match[1].upper()
    return None


def parse_raw(record):
    if record['finish_reason'] == 'length':
        return None, '', 'truncated'
    text = record['raw_completion']
    ids = record['output_token_ids']
    eos = record['eos_token_text']
    if ids and ids[-1] == record['eos_token_id'] and eos and text.endswith(eos):
        text = text[:-len(eos)]
    if record['mode'] == 'thinking' and '</think>' not in text:
        return None, '', 'missing_thinking_end'
    if '</think>' in text:
        text = text.rsplit('</think>', 1)[1]
    elif '<think>' in text:
        return None, '', 'unclosed_thinking'
    final = text.strip()
    candidates = [final]
    # Only a terminal explicit wrapper is eligible, not embedded earlier examples.
    wrapper = re.search(r'<(answer|final_answer|output|答案|dict)>\s*([^<>]*)\s*</\1>\s*$', final, flags=re.IGNORECASE)
    if wrapper:
        candidates.insert(0, wrapper[2].strip())
    fence = re.search(r'```(?:json|text)?\s*\n([^`]*)\n```\s*$', final, flags=re.IGNORECASE)
    if fence:
        candidates.insert(0, fence[1].strip())
    candidates.append(next((line.strip() for line in reversed(final.splitlines()) if line.strip()), ''))
    for candidate in candidates:
        letter = expression(candidate)
        if letter:
            return letter, candidate, None
    return None, final, 'ambiguous_or_unrecognized_final'
