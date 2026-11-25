import random
import shutil
import sys
from pathlib import Path

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
images = sorted((src / 'images').glob('*'))
random.seed(0)
random.shuffle(images)
n_val = max(1, len(images) // 5)                 # 20 % validation
for i, img in enumerate(images):
    split = 'val' if i < n_val else 'train'
    label = src / 'labels' / (img.stem + '.txt')
    for sub, f in (('images', img), ('labels', label)):
        d = dst / sub / split
        d.mkdir(parents=True, exist_ok=True)
        if f.exists():
            shutil.copy(f, d / f.name)

names = [n.strip() for n in (src / 'classes.txt').read_text().splitlines() if n.strip()]
yaml = (f'path: {dst.resolve()}\ntrain: images/train\nval: images/val\nnames:\n'
        + ''.join(f'  {i}: {n}\n' for i, n in enumerate(names)))
(dst / 'data.yaml').write_text(yaml)
print(f'{len(images) - n_val} train, {n_val} val, classes {names}')
