import time
import keymaps
import keyboard
from PIL import Image, ImageDraw, ImageFont
from waveshare_epd import epd4in2_V2
import os
import subprocess
import sys

font24 = ImageFont.truetype('Geist-Regular.otf', 18) #24

class ZeroWriter:
    def __init__(self):
        self.epd = None
        self.display_image = None
        self.display_draw = None
        self.display_updating = False
        self.cursor_position = 0
        self.text_content = ""
        self.input_content = ""
        self.previous_lines = []
        self.needs_display_update = True
        self.needs_input_update = True
        self.chars_per_line = 50
        self.lines_on_screen = 12
        self.font_size = 18
        self.line_spacing = 22
        self.scrollindex = 1
        self.console_message = ""
        self.updating_input_area = False
        self.control_active = False
        self.shift_active = False
        self.menu_mode = False
        self.menu = None
        self.parent_menu = None # used to store the menu that was open before the load menu was opened
        self.cache_file_path = os.path.join(os.path.dirname(__file__), 'data', 'cache.txt')
        self.startup_done = False
    def initialize(self):
        self.epd.init()
        self.epd.Clear()
        self.display_image = Image.new('1', (self.epd.width, self.epd.height), 255)
        self.display_draw = ImageDraw.Draw(self.display_image)
        self.last_display_update = time.time()
    def startup(self):
        #run startup script
        self.display_draw.rectangle((0, 0, 400, 300), fill=255)  # Clear display
        self.display_draw.text((55, 150), "Starting up in 7 seconds", font=font24, fill=0)
        partial_buffer = self.epd.getbuffer(self.display_image)
        self.epd.display(partial_buffer)
        
        self.needs_display_update = True
        self.needs_input_update = True
        self.startup_done = True
        print("startup finished")
        time.sleep(7)
        os.system("sudo python3 main.py")
        exit(0)
        
    def update_display(self):
        self.display_updating = True

        # Clear the main display area -- also clears input line (270-300)
        self.display_draw.rectangle((0, 0, 400, 300), fill=255)
        
        # Display the previous lines
        y_position = 270 - self.line_spacing  # leaves room for cursor input

        #Make a temp array from previous_lines. And then reverse it and display as usual.
        current_line=max(0,len(self.previous_lines)-self.lines_on_screen*self.scrollindex)
        temp=self.previous_lines[current_line:current_line+self.lines_on_screen]
        # print(temp)# to debug if you change the font parameters (size, chars per line, etc)

        for line in reversed(temp[-self.lines_on_screen:]):
          self.display_draw.text((10, y_position), line[:self.chars_per_line], font=font24, fill=0)
          y_position -= self.line_spacing

    def loop(self):
        if self.needs_display_update and not self.display_updating:
            print("updating display")
            self.update_display()
            self.update_input_area()
            self.needs_diplay_update=False
            self.typing_last_time = time.time()
            
        elif (time.time()-self.typing_last_time)<(.5): #if not doing a full refresh, do partials
            print("updating display partial")
            #the screen enters a high refresh mode when there has been keyboard input
            if not self.updating_input_area and self.scrollindex==1:
                self.update_input_area()

    def run(self):
        while True:
            self.loop()

zero_writer = ZeroWriter()

try:
    zero_writer.epd = epd4in2_V2.EPD()
    zero_writer.keyboard = keyboard
    zero_writer.initialize()
    zero_writer.run()

finally:
    zero_writer.startup()
