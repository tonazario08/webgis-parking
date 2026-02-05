from pathlib import Path
import re
s = Path('parking/utils/gis.py').read_text(encoding='utf-8')
positions = [m.start() for m in re.finditer('"""', s)]
for idx, start in enumerate(positions, start=1):
    end = positions[idx] if idx < len(positions) else None
    block = s[start:end] if end else s[start:]
    print('--- TRIPLE', idx, 'START LINE', s.count('\n',0,start)+1, 'LEN', len(block))
    print(block[:400])
    print('\n')
