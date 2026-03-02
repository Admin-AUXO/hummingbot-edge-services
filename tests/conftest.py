import sys
import os

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

for d in os.listdir(root):
    full = os.path.join(root, d)
    if os.path.isdir(full) and d.endswith("-service"):
        sys.path.insert(0, full)

sys.path.insert(0, root)
