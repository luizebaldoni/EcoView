from pathlib import Path
import sys

f = Path(__file__).resolve().parent.parent / 'config' / 'settings.py'
if not f.exists():
    print('settings.py not found at', f)
    sys.exit(1)

lines = f.read_text(encoding='utf-8').splitlines()
N = len(lines)
found = []
min_block = 3
max_block = max(3, N//2)
# Search for largest duplicated blocks first
for k in range(max_block, min_block-1, -1):
    seen = {}
    for i in range(0, N-k+1):
        block = '\n'.join(lines[i:i+k])
        h = hash(block)
        if h in seen:
            # check actual content equality to avoid hash collision
            seen[h].append(i)
        else:
            seen[h] = [i]
    for h, idxs in seen.items():
        if len(idxs) > 1:
            # verify content equality
            for a in range(len(idxs)):
                for b in range(a+1, len(idxs)):
                    ia = idxs[a]
                    ib = idxs[b]
                    if '\n'.join(lines[ia:ia+k]) == '\n'.join(lines[ib:ib+k]):
                        found.append((k, ia, ib))

if not found:
    print('No duplicated blocks of >= {} lines found.'.format(min_block))
else:
    print('Found duplicated blocks:')
    for k, ia, ib in found:
        print('\n-- Block size: {} lines --'.format(k))
        print('Occurrence 1: lines {}-{}'.format(ia+1, ia+k))
        print('Occurrence 2: lines {}-{}'.format(ib+1, ib+k))
        print('--- Block preview ---')
        print('\n'.join(lines[ia:ia+min(50,k)]))
        print('---------------------')

