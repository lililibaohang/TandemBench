"""Score normalized choices. Does not parse raw model text or call a model."""
import argparse
import json
from collections import defaultdict
from pathlib import Path


def score(answers, predictions, samples):
    if type(samples) is not int or samples<1 or not answers:
        raise ValueError('Positive samples and nonempty evaluation answers required')
    for answer in answers:
        group=answer.get('condition','decision')
        field='correct_letter' if group=='decision' else 'meta_letter'
        if group not in ('decision','removed','retained') or answer.get(field) not in ('A','B','C','D'):
            raise ValueError('Invalid evaluation condition or answer letter')
    gold = {x['id']: x for x in answers}
    if len(gold) != len(answers):
        raise ValueError('duplicate answer IDs')
    seen = set()
    totals = defaultdict(int)
    correct = defaultdict(int)
    for pred in predictions:
        item, sample = pred['id'], pred['sample']
        if item not in gold or type(sample) is not int or not 0 <= sample < samples:
            raise ValueError('unknown ID or invalid sample index')
        if (item, sample) in seen:
            raise ValueError('duplicate prediction')
        seen.add((item, sample))
        target = gold[item]
        group = target.get('condition', 'decision')
        totals[group] += 1
        choice = pred.get('choice')
        if choice not in ('A', 'B', 'C', 'D', None):
            raise ValueError('choice must be A/B/C/D or null for invalid')
        if group == 'decision':
            ok = choice == target['correct_letter']
        elif group == 'removed':
            ok = choice == target['meta_letter']
        elif group == 'retained':
            ok = choice in ('A', 'B', 'C', 'D') and choice != target['meta_letter']
        else:
            raise ValueError('unknown evaluation condition')
        correct[group] += int(ok)
    if len(seen) != len(gold) * samples:
        raise ValueError('incomplete predictions; every rendered item and sample is required')
    rates = {k: correct[k] / n for k, n in totals.items()}
    result = {'records': len(seen), 'samples_per_item': samples, 'rates': rates}
    if 'decision' in rates:
        result['DA'] = rates['decision']
    if {'removed', 'retained'} <= rates.keys():
        result['VA'] = (rates['removed'] + rates['retained']) / 2
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--answers', type=Path, required=True)
    p.add_argument('--predictions', type=Path, required=True)
    p.add_argument('--samples', type=int, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.samples < 1:
        p.error('--samples must be positive')
    load = lambda path: [json.loads(line) for line in path.open() if line.strip()]
    result = score(load(a.answers), load(a.predictions), a.samples)
    with a.out.open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')


if __name__ == '__main__':
    main()
