import os
from src.sketch_artist import draw_sketch_for_phrase
prompt = os.environ.get('PROMPT', 'every night in my dreams')
img = draw_sketch_for_phrase(prompt, 720, 1280)
img.save('hand_sketch_test.png')
print(f'Saved: hand_sketch_test.png ({img.size[0]}x{img.size[1]})')
