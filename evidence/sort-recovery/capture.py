"""Render production terminal cells as review images, not native screenshots."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from riposte.terminal.controller import Controller
from riposte.terminal.output import Presentation
from riposte.terminal.render import render

HERE = Path(__file__).parent
font = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 16)
bold = ImageFont.truetype('C:/Windows/Fonts/consolab.ttf', 16)
controller = Controller(None, Presentation(no_animation=True))
for name, width, height in [('home-small',72,24),('home-wide',100,34),('browser-small',72,24)]:
    if name.startswith('browser'):
        controller.begin_action('riposte')
        picker = controller.state.page.result
        picker.enter(Path('.tmp/sort-native-home/Pictures').absolute())
        controller.state.page.rows = picker.rows()
    surface = render(controller.state,width,height,0)
    image = Image.new('RGB',(width*10,height*21),'#20242a')
    draw = ImageDraw.Draw(image)
    for y,row in enumerate(surface.cells):
        for x,cell in enumerate(row):
            color=surface.palette.get(cell.fg,cell.fg)
            if color == 'default': color = '#D8DEE9'  # simulated host foreground
            draw.text((x*10,y*21),cell.char,font=bold if cell.bold else font,fill=color)
    image.save(HERE/(name+'.png'))
    (HERE/(name+'.txt')).write_text(surface.plain(),encoding='utf-8')
controller.shutdown()
