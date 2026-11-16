# Example macro: draws a grid over the canvas

w, h = canvas.get_size()
canvas.push_undo()

step = 40
for x in range(0, w, step):
    canvas.draw_form('line', (x, 0), (x, h - 1), width=1, color='#aaaaaa', transparent=True)

for y in range(0, h, step):
    canvas.draw_form('line', (0, y), (w - 1, y), width=1, color='#aaaaaa', transparent=True)

canvas.commit()
