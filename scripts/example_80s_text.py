# SimpleDraw script example
# creates a shadowed text in 80s style


canvas.set_size(220, 60)
canvas.push_undo()

# Dark background
canvas.clear()

# Shadow layers (offset copies in deep magenta/purple, fading outward)
for ox, oy, col in [
    (4, 4, '#3d0040'),
    (3, 3, '#6b006e'),
    (2, 2, '#9b00a0'),
]:
    canvas.draw_text('SimpleDraw', (10 + ox, 8 + oy),
                     font='Impact', size=28, bold=True,
                     color=col, bg_transparent=True)

# Cyan glow halo
for ox, oy in [(-1,0),(1,0),(0,-1),(0,1)]:
    canvas.draw_text('SimpleDraw', (10 + ox, 8 + oy),
                     font='Impact', size=28, bold=True,
                     color='#00eeff', bg_transparent=True)

# Main neon text — hot pink
canvas.draw_text('SimpleDraw', (10, 8),
                 font='Impact', size=28, bold=True,
                 color='#ff2d9b', bg_transparent=True)

canvas.commit()
