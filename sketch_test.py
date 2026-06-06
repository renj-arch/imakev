import os, sys
from src.sketch_engine import generate_sketch_scene
prompt = os.environ.get('PROMPT', 'every night in my dreams')
img = generate_sketch_scene(prompt, 720, 1280)
img.save('hand_sketch_test.png')
print(f'Saved: hand_sketch_test.png ({img.size[0]}x{img.size[1]})')
