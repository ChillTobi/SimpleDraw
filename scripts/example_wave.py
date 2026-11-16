# SimpleDraw script example
# draws grayscale circles with an outline color that is a sinewave

import math

can_size= 265
canvas.set_size(can_size, can_size)
canvas.push_undo()

# Dark background
canvas.clear()
canvas.set_background_color(255,255,255)


circle_color= 0
start_pos= (can_size/2,can_size/2)

max_wave= int((can_size-5)/2)
for radius in range (1,max_wave,1):
    circle_color= int(127*math.sin(2*math.pi*radius/max_wave-128)+128)
    print(radius, circle_color)
    canvas.draw_form('circle', start_pos, radius, 1, (circle_color, circle_color, circle_color),  (0,0,0), True, 0, 0, False, True)
    
#canvas.apply_effect('smooth', 1)

canvas.commit()