from pathlib import Path
s = Path('parking/utils/gis.py').read_text(encoding='utf-8')
print('count triple quotes:', s.count('"""'))
import re
for i,m in enumerate(re.finditer('"""', s), start=1):
    print(f"{i}: line {s.count('\n', 0, m.start()) + 1}")
