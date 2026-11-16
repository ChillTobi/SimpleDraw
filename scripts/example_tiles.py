# SimpleDraw script example
# draws 4 circles with the same distance to each other.
# the cricles represent a fireball or similar. This example is probably good to use as tile texture in a game

canvas.set_size(64, 16)
canvas.push_undo()

# Dark background
canvas.set_background_color(0,255,0)
canvas.clear()


w, h= canvas.get_size()
x_offset= w/ 8
start_pos= (x_offset, h/2-1)
color_yellow= (230,186,29)
start_radius= 1


for index in range (0,4,1):
    start_pos= (x_offset + (index * 16), start_pos[1]) 
    canvas.draw_form('circle', start_pos, start_radius+index, 1, color_yellow,  color_yellow, False, 0, 0, False)
    
canvas.apply_effect('smooth', 1)

for index in range (0,4,1):
    start_pos= (x_offset + (index * 16), start_pos[1]) 
    canvas.draw_form('circle', start_pos, start_radius+index-1, 1, color_yellow,  color_yellow, False, 0, 0, False)

#canvas.apply_effect('grayscale')
#canvas.apply_effect('invert')

canvas.commit()

