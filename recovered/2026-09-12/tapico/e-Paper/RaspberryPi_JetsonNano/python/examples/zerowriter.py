import time
import keymaps
import qrcode
import socket
import keyboard
import shutil
import signal
import os
import subprocess
import threading

from gmailhandle import GmailCredentials
from PIL import Image, ImageDraw, ImageFont

delay = .100 #standard delay v2.2, 2.1 can use 0
font24 = ImageFont.truetype('Geist-Regular.otf', 18)

class Menu:
    def __init__(self, display_draw, epd, display_image):
        self.display_draw = display_draw
        self.epd = epd
        self.display_image = display_image
        self.menu_items = []
        self.selected_item = 0
        self.inputMode = False
        self.input_content = ""
        self.cursor_position = 0
        self.screenupdating = False
        self.inputlabel = "input"
        self.ending_content=""

    def addItem(self, text, action, callback):
        self.menu_items.append({'text': text, 'action': action, 'callback': callback})

    def up(self):
        self.selected_item -= 1
        if self.selected_item < 0:
            self.selected_item = len(self.menu_items) - 1
        self.display()
        time.sleep(delay)
    
    def down(self):
        self.selected_item += 1
        if self.selected_item > len(self.menu_items) - 1:
            self.selected_item = 0
        self.display()
        time.sleep(delay)

    def select(self):
        self.menu_items[self.selected_item]['action']()

    def display(self):
        # print("menu.display A")
        self.display_draw.rectangle((0, 0, 400, 300), fill=255)
        y_position = 10
        
        start_index = max(0, self.selected_item - 5)  # Start index for display
        end_index = min(len(self.menu_items), start_index + 10)  # End index for display
        
        # Iterate over the range of menu items to display
        for index in range(start_index, end_index):
            prefix = self.selected_item == index and "> " or "  "  # Prefix for selected item
            item_text = self.menu_items[index]['text']  # Get the text of the menu item
            self.display_draw.text((10, y_position), prefix + item_text, font=font24, fill=0)
            y_position += 30  # Increment Y position for next menu item

        partial_buffer = self.epd.getbuffer(self.display_image)
        self.epd.display_Partial(partial_buffer)
        time.sleep(delay)
        # print("menu.display B")

    def save_as(self):
        self.ending_content=""
        self.getInput("File Name", self.input_content)

    # def get_gmail_id(self):
        # self.ending_content="@gmail.com"
        # self.getInput("ID", self.input_content)

    # def get_gmail_pass(self):
        # self.ending_content=""
        # self.getInput("PW", self.input_content)

    def delete_file(self):
        self.ending_content=""
        self.getInput("'delete' to confirm", self.input_content)

    def request_network_pw(self):
        self.ending_content=""
        self.getInput("PW", self.input_content)
        return

    def partial_update(self):
        print("menu.partial_update")
        self.display_draw.rectangle((0, 270, 400, 300), fill=255)  # Clear display
        temp_content = self.inputlabel + ": " + self.input_content + self.ending_content
        # Draw input line text
        self.display_draw.text((10, 270), str(temp_content), font=font24, fill=0)        
        partial_buffer = self.epd.getbuffer(self.display_image)
        self.epd.display_Partial(partial_buffer)
        time.sleep(delay)

    def getInput(self, prompt, callback):
        self.inputMode = True
        self.input_content = ""
        self.cursor_position = 0
        self.inputlabel = prompt

    def cleanupInput(self):
        # print("menu.cleanupInput A")
        self.inputMode = False
        self.input_content=""
        time.sleep(delay) 
        self.partial_update()
        # print("menu.cleanupInput B")

    def consolemsg(self, text):
        time.sleep(delay)
        self.display_draw.rectangle((0, 0, 400, 300), fill=255)  # Clear display
        temp_content = text
        # Draw input line text
        self.display_draw.text((10, 270), str(temp_content), font=font24, fill=0)        
        partial_buffer = self.epd.getbuffer(self.display_image)
        self.epd.display_Partial(partial_buffer)
        time.sleep(2)
        self.display_draw.rectangle((0, 0, 400, 300), fill=255)  # Clear display
        partial_buffer = self.epd.getbuffer(self.display_image)
        self.epd.display_Partial(partial_buffer)
        time.sleep(delay)

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
        self.needs_display_update = False
        # self.needs_input_update = False
        self.chars_per_line = 47
        self.lines_on_screen = 12
        self.font_size = 18
        self.line_spacing = 22
        self.scrollindex = 1
        self.console_message = ""
        self.typing_last_time = 0
        self.updating_input_area = False
        self.input_mode = True
        self.control_active = False
        self.shift_active = False
        self.menu_mode = False
        self.screensaver_mode = False
        self.menu = None
        self.manual_network=""
        self.parent_menu = None # used to store the menu that was open before the load menu was opened
        self.server_address = "not active"
        self.cache_file_path = os.path.join(os.path.dirname(__file__), 'data', 'cache.txt')
        self.doReset = False
        self.inactivity_timer = None
        self.inactivity_timeout = 60 #60 = 1 min of inactivity
        self.screensaver_pause = 15 #time for the screensaver pauses between screens
        self.screensaver_active = False
        self.skip_pause = False

    def initialize(self):
        self.epd.init()
        self.epd.Clear()
        self.display_image = Image.new('1', (self.epd.width, self.epd.height), 255)
        self.display_draw = ImageDraw.Draw(self.display_image)
        self.last_display_update = time.time()
        print("initialize 1")

        #comment these two lines if you want to keep terminal interupts
        #signal.signal(signal.SIGINT, signal.SIG_IGN)
        #signal.signal(signal.SIGTSTP, signal.SIG_IGN)

        self.start_server()

        self.keyboard.on_press(self.handle_key_press, suppress=False) #handles modifiers and shortcuts
        self.keyboard.on_release(self.handle_key_up, suppress=True)

        self.menu = Menu(self.display_draw, self.epd, self.display_image)
        self.populate_main_menu()

        self.load_menu = Menu(self.display_draw, self.epd, self.display_image)
        self.populate_load_menu()

        self.networks_menu = Menu(self.display_draw, self.epd, self.display_image)
        self.populate_networks_menu()

        # self.gmail_menu = Menu(self.display_draw, self.epd, self.display_image)
        # self.populate_gmail_menu()

        self.file_sample_menu = Menu(self.display_draw, self.epd, self.display_image)

        #second init should catch if initial init has errors.
        # time.sleep(.25)
        # self.epd.init()
        # self.epd.Clear()
        #self.check_nmcli()


    def get_ssid(self):
        try:
            raw_wifi = subprocess.check_output(['iwgetid', '-r'])
            data_strings = raw_wifi.decode('utf-8').split()
            return data_strings
        except Exception as e:
            return(e)
            print("error getting current SSID")

    def start_server(self):
        try:
            print("starting data server...")
            current_directory = os.path.join(os.getcwd(),"data")
            subprocess.Popen(["python", "-m", "http.server", str(8000)], cwd=current_directory, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.server_address=str(socket.gethostname() + ".local:8000")
        except Exception as e:
            print("error starting server...")

    def show_load_menu(self):
        self.parent_menu = self.menu
        self.populate_load_menu()
        self.menu = self.load_menu
        self.menu.display()

    def show_networks_menu(self):
        self.parent_menu = self.menu
        self.populate_networks_menu()
        self.menu = self.networks_menu
        self.menu.display()

    # def show_gmail_menu(self):
        # self.parent_menu = self.menu
        # self.populate_gmail_menu()
        # self.menu = self.gmail_menu
        # self.menu.display()
    
    def show_file_sample_menu(self):
        self.parent_menu = self.menu
        self.display_file_sample_menu()
        self.menu = self.file_sample_menu
        # self.menu.display()

    def hide_child_menu(self):
        self.menu = self.parent_menu
        self.populate_main_menu()
        self.menu.display()

    def populate_main_menu(self):
        self.menu.menu_items.clear()
        self.menu.addItem("Wifi: " + str(self.get_ssid()), lambda: self.show_networks_menu(), None)
        self.menu.addItem("Files: " + str(self.server_address), lambda: None, None)
        self.menu.addItem("About", lambda: self.show_screensaver(), None)
        self.menu.addItem("Power Off", lambda: self.power_down(), None)
        # self.menu.addItem("File Select", lambda: self.show_file_sample_menu(), None)
        # self.menu.addItem("Save As", lambda: self.menu.save_as(), lambda: self.save_as_file(self.menu.input_content))
        # self.menu.addItem("New", lambda: self.new_file(), None)
        # self.menu.addItem("Load", lambda: self.show_load_menu(), None)
        # self.menu.addItem("", lambda: print(""), None)
        # self.menu.addItem("Gmail Yourself", lambda: self.gmail_send(), None)
        # self.menu.addItem("QR Code", lambda: self.display_qr_code(), None)
        # self.menu.addItem("Gmail Config", lambda: self.show_gmail_menu(), None)
        # self.menu.addItem("", lambda: print(""), None)

    def populate_load_menu(self):
        self.load_menu.menu_items.clear()
        data_folder_path = os.path.join(os.path.dirname(__file__), 'data')
        try:
            files = [f for f in os.listdir(data_folder_path) if os.path.isfile(os.path.join(data_folder_path, f)) and f.endswith('.txt')]
            files.sort(key=lambda x: os.path.getmtime(os.path.join(data_folder_path, x)), reverse=True)

            self.load_menu.addItem("<- Back | Del: ctrl+bkspc", self.hide_child_menu, None)
            self.load_menu.addItem("cache.txt autosave file", lambda f="cache.txt": self.load_file_into_previous_lines("cache.txt"), None)

            for filename in files:
                if filename != "cache.txt":
                    self.load_menu.addItem(filename, lambda f=filename: self.load_file_into_previous_lines(f), None)
        except Exception as e:
            self.load_menu.addItem("Error: "+{e}, self.hide_child_menu, None)
            print(f"Failed to list files in {data_folder_path}: {e}")

    def move_to_archive(self):
        selected_item = self.load_menu.menu_items[self.load_menu.selected_item]['text']
        try:
            if selected_item not in ["<- Back | Del: ctrl+bkspc", "cache.txt autosave file"]:  # Ensure it's not a special menu item
                selected_file = os.path.join(os.path.dirname(__file__), 'data', selected_item)
                print(selected_file)
                shutil.move(selected_file, os.path.join(os.path.dirname(__file__), 'data/archive'))
                print(f"Moved {selected_item} to Archive folder.")
                self.menu.consolemsg(f"Deleted {selected_item}.")
                self.populate_load_menu()
                self.menu.display()
        except Exception as e:
            self.menu.consolemsg(f"{e}.")
            print(e)        

    def populate_networks_menu(self):
        self.networks_menu.menu_items.clear()
        try:
            available_networks = self.get_available_wifi_networks()
            self.networks_menu.addItem("<- Back", self.hide_child_menu, None)
            self.networks_menu.addItem("Manually Enter SSID", lambda: self.menu.getInput("SSID", self.input_content), lambda: self.update_manual_ssid(self.menu.input_content))
            if self.manual_network!="":
                self.networks_menu.addItem(self.manual_network, lambda: self.menu.request_network_pw(), lambda: self.connect_to_network(self.manual_network,(self.menu.input_content)))
            for network in available_networks:
                if network != "--":
                    self.networks_menu.addItem(network, lambda n=network: self.menu.request_network_pw(), lambda n=network: self.connect_to_network(n,(self.menu.input_content)))
        except Exception as e:
            self.networks_menu.addItem(f"Failed: {e}", self.hide_child_menu, None)
            print(f"Failed: {e}")

    def update_manual_ssid(self, networkname):
        self.manual_network=networkname
        self.populate_networks_menu()
        print("new network: "+ networkname)

    # def populate_gmail_menu(self):
    #     gmusername = str(GmailCredentials.load_gmail_username())
    #     gmpassword = str(GmailCredentials.load_gmail_password())
    #     self.gmail_menu.menu_items.clear()
    #     self.gmail_menu.addItem("<- Back", self.hide_child_menu, None)
    #     self.gmail_menu.addItem("Gmail: " + gmusername, lambda: self.menu.get_gmail_id(), lambda: self.set_gmail_id(self.menu.input_content))
    #     self.gmail_menu.addItem("App PW: " + ('*' * len(gmpassword)), lambda: self.menu.get_gmail_pass(), lambda: self.set_gmail_pass(self.menu.input_content))
    #     self.gmail_menu.addItem("Connection: " + GmailCredentials.check_connection(gmusername,gmpassword), lambda: print(GmailCredentials.check_connection(gmusername,gmpassword)), None)
    #     self.gmail_menu.addItem("=============================", lambda: None, None)
    #     self.gmail_menu.addItem("This connects a gmail account.", lambda: None, None)
    #     self.gmail_menu.addItem("Enable App Password in 2FA.", lambda: None, None)
    #     self.gmail_menu.addItem("Use the App Password. Use a", lambda: None, None)
    #     self.gmail_menu.addItem("new gmail account for security.", lambda: None, None)
    

    # def gmail_send(self):
    #     try:
    #         gmusername = str(GmailCredentials.load_gmail_username())
    #         gmpassword = str(GmailCredentials.load_gmail_password())
    #         contents = self.previous_lines
    #         GmailCredentials.send_gmail(gmusername, gmpassword, contents)
    #         self.hide_menu()
    #         time.sleep(delay)
    #         if self.menu_mode:
    #             self.menu.consolemsg(">>> Gmail Sent.")
    #         else:
    #             self.consolemsg(">>> Gmail Sent.")

    #     except Exception as e:
    #         self.hide_menu()
    #         time.sleep(delay)
    #         if self.menu_mode:
    #             self.menu.consolemsg(">>> Gmail Failed.")
    #         else:
    #             self.consolemsg(">>> Gmail Failed.")

    def connect_to_network(self, network, password):
        self.connect_to_wifi(network, password)
        return

    def check_nmcli(self):
        print("checking for networking")
        try:
            # Run nmcli to check the status of NetworkManager
            process = subprocess.Popen(['nmcli', 'general', 'status'], 
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate(timeout=5)
            print(stdout)
            print(stderr)
            if b'Error' in stderr:
                print("NetworkManager not running.")
                print("If you want network management, run: sudo systemctl enable NetworkManager")
                print("This will require you to reconfigure network in raspi-config.")
                print("You'll need a HDMI cable, since SSH won't work.")
                # Enable NetworkManager
                # subprocess.run(['sudo', 'systemctl', 'enable', 'NetworkManager'])
                # time.sleep(1)
                # subprocess.run(['sudo', 'systemctl', 'start', 'NetworkManager'])
                # time.sleep(1)
            else:
                print("NetworkManager is enabled.")
        except subprocess.TimeoutExpired:
            print("Networking not detected or configured.")

    def connect_to_wifi(self, ssid, password):
        try:
            process = subprocess.Popen(['nmcli', 'device', 'wifi', 'connect', ssid, 'password', password], 
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # Wait for the command to finish, with a timeout of 5 seconds
            stdout, stderr = process.communicate(timeout=5)
            # Check if the command was successful
            if process.returncode == 0:
                print(f"Connected to WiFi: {ssid}")
                self.menu.consolemsg(f"Connected to: {ssid}")
                return True
            else:
                print(f"Error connecting to WiFi: {stderr.decode()}")
                self.menu.consolemsg(f"Error: {stderr.decode()}")
                return False
        except subprocess.TimeoutExpired:
            print("Timeout error.")
            self.menu.consolemsg("Error: Connection Timeout.")
            return False

    def consolemsg(self, text):
        self.console_message = text

    def load_file_into_previous_lines(self, filename):
        file_path = os.path.join(os.path.dirname(__file__), 'data', filename)
        try:
            with open(file_path, 'r') as file:
                lines = file.readlines()
                self.previous_lines = [line.strip() for line in lines]
                self.input_content = ""
                self.cursor_position = 0
                # self.consolemsg(filename)
        except Exception as e:
            self.consolemsg(f"[Error loading file]")
        finally:
            self.hide_menu()

    def load_file_into_previous_lines_silent(self, filename):
        file_path = os.path.join(os.path.dirname(__file__), 'data', filename)
        try:
            with open(file_path, 'r') as file:
                lines = file.readlines()
                self.previous_lines = [line.strip() for line in lines]
                self.cursor_position = len(self.input_content)
                self.input_content = ""
        except Exception as e:
            self.consolemsg(f"[Error loading file]")
        finally:
            self.hide_menu()

    def show_screensaver(self):
        #this stuff works
        # self.screensaver_mode = True
        # self.temp_input=self.input_content
        # self.lines_on_screen = self.lines_on_screen + 1
        # self.input_mode = False

        # self.load_screensaver("tapicoinfo1.txt")

        #screensaver threading code
        
        # self.temp_input=self.input_content
        # self.lines_on_screen = self.lines_on_screen + 1
        if self.screensaver_active:
            return
        
        self.screensaver_active = True #Set the flag to true to indicate that the screensaver is on
        print("screensaver start")
        self.input_mode = False
        filename = ["info1.txt", "info2.txt", "info3.txt", "info4.txt"]
        threading.Thread(target=self.load_screensaver, args=(filename,)).start()
        print("screensaver end")

    def load_screensaver(self, filename):
        #this stuff works:
        # file_path = os.path.join(os.path.dirname(__file__), 'data', filename)
        # try:
        #     with open(file_path, 'r') as file:
        #         lines = file.readlines()
        #         self.previous_lines = [line.strip() for line in lines]
        # finally:
        #     self.hide_menu()

        #screensaver threading code
        while not self.input_mode:
            for file in filename:
                if not self.input_mode:
                    self.previous_lines.clear()
                    self.full_display_refresh()
                if self.input_mode:
                    break
                self.load_file_into_previous_lines_silent(file)
                self.update_display()
                start_time = time.time()
                while time.time() - start_time < self.screensaver_pause:
                    if self.skip_pause:
                        self.skip_pause = False # Reset the flag
                        break
                    time.sleep(delay)
        self.clear_screensaver()
    
    def clear_screensaver(self):
        #screensaver threading code
        # self.lines_on_screen = self.lines_on_screen - 1
        # self.input_content = self.temp_input
        self.screensaver_active = False #Set the screensaver flag to indicate that it's off
        self.load_file_into_previous_lines_silent("cache.txt")
        self.previous_lines.clear()
        self.input_content = ""
        # self.needs_display_update = True
        self.update_display()
        time.sleep(.5)
        self.input_mode = True #this goes back to the input mode writing screen
        self.update_input_area()
        self.reset_inactivity_timer() #reset the inactivity timer
    
    def hide_screensaver (self):
        #this stuff works:
        # time.sleep(delay*2)
        # self.lines_on_screen = self.lines_on_screen - 1
        # self.screensaver_mode = False
        # self.input_content = self.temp_input
        # self.load_file_into_previous_lines_silent("cache.txt")
        # self.input_mode = True
        # self.needs_display_update = True
        # # print("input mode: " + str(self.input_mode))
        # # print("screensaver mode: "+ str(self.screensaver_mode))
        # print("hide screensaver")

        #screensaver threading code
        self.clear_screensaver()

    def get_available_wifi_networks(self):
        try:
            result = subprocess.run(['nmcli', '-f', 'SSID', 'dev', 'wifi', 'list'], capture_output=True, text=True)
            output = result.stdout.strip()
            networks = [line.split()[0] for line in output.split('\n')[1:] if line.strip()]
            return networks
        except Exception as e:
            print(f"Error getting available WiFi networks: {e}")
            return []

    def new_file(self):
        self.save_previous_lines(self.cache_file_path, self.previous_lines)
        self.previous_lines.clear()
        self.input_content = ""
        self.consolemsg("[New]")
        self.hide_menu()

    def power_down(self, debug=False): #set to False for the degree show
        self.stop_inactivity_timer()
        self.save_previous_lines(self.cache_file_path, self.previous_lines)
        self.previous_lines.clear()
        self.epd.init()
        self.epd.Clear()
        self.display_draw.rectangle((0, 0, 400, 300), fill=255)  #Clear display
        self.display_draw.text((146, 140), "Tapico Typer", font=font24, fill=0)
        partial_buffer = self.epd.getbuffer(self.display_image)
        self.epd.display_Partial(partial_buffer)
        time.sleep(1)
        self.epd.sleep()
        if not debug: #only run the poweroff command if not debugging
            time.sleep(1)
            subprocess.run(['sudo', 'poweroff', '-f'])
        self.needs_display_update = False

    def save_previous_lines(self, file_path, lines):
      try:
          # Ensure the directory exists
          os.makedirs(os.path.dirname(file_path), exist_ok=True)
          # Check if the file is writable or create it if it doesn't exist
          with open(file_path, 'a') as file:
              pass
          # Clear the file content before writing
          with open(file_path, 'w') as file:
              print("Saving to file:", file_path)
              for line in lines:
                  file.write(line + '\n')
      except IOError as e:
          self.consolemsg("[Error saving file]")
          print("Failed to save file:", e)

    def hide_menu(self):
        time.sleep(delay*2)
        self.menu_mode = False
        self.needs_display_update = True

    def show_menu(self):
        self.populate_main_menu()
        self.menu_mode = True
        if self.parent_menu != None:
            self.menu = self.parent_menu
        self.selected_item = 0
        self.menu.display()
    
    def display_file_sample_menu(self):
        self.menu_mode = True
        try:
            # Load the image
            image_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'FSM_Round.png')
            fsm_image = Image.open(image_path)
            # Resize image if necessary
            fsm_image = fsm_image.resize((self.epd.width, self.epd.height), Image.ANTIALIAS)
            # Convert the image to 1-bit color
            fsm_image = fsm_image.convert('1')
            # Clear the display image
            self.display_draw.rectangle((0, 0, self.epd.width, self.epd.height), fill=255)
            # Paste the file sample menu into the display image
            self.display_image.paste(fsm_image,(0,0))
            # Update the display with the new image
            partial_buffer = self.epd.getbuffer(self.display_image)
            self.epd.display_Partial(partial_buffer)
            time.sleep(delay)
        except Exception as e:
            self.menu.consolemsg(e)

    # def display_qr_code(self):
    #     self.menu_mode = True        
    #     try:
    #         # Combine all previous lines into a single string
    #         qr_data = 'mailto:example@example.com?body=' + ' '.join(self.previous_lines)
    #         # Generate QR code
    #         # giving it no version will allow it to auto-detect the smallest version that will fit the data
    #         # currently does not handle extremely large files
    #         qr = qrcode.QRCode(
    #             error_correction=qrcode.constants.ERROR_CORRECT_L,
    #             box_size=2,
    #             border=4,
    #         )
    #         qr.add_data(qr_data)
    #         qr.make(fit=True)
    #         qr_img = qr.make_image(fill='black', back_color='white')
    #         # Convert QR code image to match the display's image mode
    #         qr_img_converted = qr_img.convert('1')
    #         # Save QR code to the filesystem
    #         qr_img_save_path = os.path.join(os.path.dirname(__file__), 'data', 'qr_code.png')
    #         qr_img.save(qr_img_save_path)
    #         print(f"QR code saved to {qr_img_save_path}")

    #         # Calculate position to center QR code on the display
    #         qr_x = (self.epd.width - qr_img_converted.width) // 2
    #         qr_y = (self.epd.height - qr_img_converted.height) // 2
    #         # Clear the display image
    #         self.display_draw.rectangle((0, 0, self.epd.width, self.epd.height), fill=255)
    #         # Paste the QR code onto the display image
    #         self.display_image.paste(qr_img_converted, (qr_x, qr_y))
    #         # Update the display with the new image
    #         partial_buffer = self.epd.getbuffer(self.display_image)
    #         self.epd.display_Partial(partial_buffer)
    #         time.sleep(delay)
    #     except Exception as e:
    #         self.menu.consolemsg(e)

    def full_display_refresh(self):
        self.epd.init()
        self.epd.Clear()
        self.update_display()
        time.sleep(delay)
        self.update_input_area()

    def update_display(self):
        # print("UD Needs display update: " + str(self.needs_display_update))
        self.display_updating = True
        self.display_draw.rectangle((0, 0, 400, 300), fill=255)
        
        # Display the previous lines based on whether it's input mode or not
        # if self.input_mode:
            # y_position = 270 - self.line_spacing  # leave room for cursor input
        # if not self.input_mode:
        #     y_position = 294 - self.line_spacing  # does not leave room for cursor input

        # Display the previous lines
        y_position = 270 - self.line_spacing  # leaves room for cursor input

        #Make a temp array from previous_lines. And then reverse it and display as usual.
        current_line=max(0,len(self.previous_lines)-self.lines_on_screen*self.scrollindex)
        temp=self.previous_lines[current_line:current_line+self.lines_on_screen]
        # print(temp)# to debug if you change the font parameters (size, chars per line, etc)

        for line in reversed(temp[-self.lines_on_screen:]):
          self.display_draw.text((10, y_position), line[:self.chars_per_line], font=font24, fill=0)
          y_position -= self.line_spacing

        #Display Console Message
        if self.console_message != "":
            # self.display_draw.rectangle((300, 270, 400, 300), fill=255)
            # self.display_draw.text((200, 270), self.console_message, font=font24, fill=0)
            self.console_message = ""
            return
        
        #generate display buffer for display
        partial_buffer = self.epd.getbuffer(self.display_image)
        self.epd.display_Partial(partial_buffer)
        self.last_display_update = time.time()
        self.display_updating = False
        self.needs_display_update = False

    def update_input_area(self):
        #if not self.menu_mode:
        if not self.updating_input_area and self.scrollindex==1:
            self.updating_input_area = True
            cursor_index = self.cursor_position
            self.display_draw.rectangle((0, 270, 400, 300), fill=255)  # Clear display
            if self.input_mode == True: #show cursor if inputting
                temp_content = self.input_content[:cursor_index] + "|" + self.input_content[cursor_index:]
            else: #hide cursor if not actually using input area for input i.e. screensaver
                temp_content = self.input_content[:cursor_index] + "" + self.input_content[cursor_index:]
            self.display_draw.text((10, 270), str(temp_content), font=font24, fill=0)
            #self.updating_input_area = True
            partial_buffer = self.epd.getbuffer(self.display_image)
            self.epd.display_Partial(partial_buffer)
            # print("update_input_area")
            self.updating_input_area = False

    def insert_character(self, character):
        cursor_index = self.cursor_position
        
        if cursor_index <= len(self.input_content):
            # Insert character in the text_content string
            self.input_content = self.input_content[:cursor_index] + character + self.input_content[cursor_index:]
            self.cursor_position += 1  # Move the cursor forward
        
        # self.needs_input_update = True

    def delete_character(self):
        if self.cursor_position > 0:
            # Remove the character at the cursor position
            self.input_content = self.input_content[:self.cursor_position - 1] + self.input_content[self.cursor_position:]
            self.cursor_position -= 1  # Move the cursor back
            # self.needs_input_update = True
        #No characters on the line, move up to previous line
        elif len(self.previous_lines) > 0:
            self.input_content = ""
            self.input_content = self.previous_lines[len(self.previous_lines)-1]
            self.previous_lines.pop(len(self.previous_lines)-1)
            self.cursor_position = len(self.input_content)
            self.needs_display_update = True

    def delete_previous_word(self):
        #find the location of the last word in the line
        last_space = self.input_content.rstrip().rfind(' ', 0, self.chars_per_line)
        sentence = ""
        #Remove previous word
        if last_space >= 0:
            sentence = self.input_content[:last_space+1]
        self.input_content = sentence
        self.cursor_position = len(self.input_content) 
        #self.needs_display_update = True
                
    def handle_key_up(self, e): 
        if e.name == 'ctrl': #if control is released
            self.control_active = False
            print ("ctrl is up again")
        if e.name == 'shift': #if shift is released
            self.shift_active = False
            print ("shift is up again")

    def save_file(self):
        timestamp = time.strftime("%m%d")  # Format: MMDD
        prefix = ''.join(self.previous_lines)[:20]
        alphanum_prefix = ''.join(ch for ch in prefix if ch.isalnum())
        filename = os.path.join(os.path.dirname(__file__), 'data', f'{timestamp}_{alphanum_prefix}.txt')
        self.previous_lines.append(self.input_content)
        self.save_previous_lines(filename, self.previous_lines)
        self.save_previous_lines(self.cache_file_path, self.previous_lines)
        self.input_content = self.previous_lines.pop(len(self.previous_lines)-1)
        self.consolemsg("[Saved]")
        time.sleep(delay*5)
        self.needs_display_update = True

    def save_as_file(self, userinput):
        # self.menu.input_content = ""
        print("save_as_file A")
        # self.menu.display()
        # self.menu.cleanupInput()
        # self.hide_menu()
        # self.hide_child_menu
        filename = os.path.join(os.path.dirname(__file__), 'data', f'{userinput}.txt')
        self.previous_lines.append(self.input_content)
        self.save_previous_lines(filename, self.previous_lines)
        self.save_previous_lines(self.cache_file_path, self.previous_lines)
        self.input_content = self.previous_lines.pop(len(self.previous_lines)-1)
        self.menu.consolemsg("[Save As: " + f'{userinput}.txt' + "]")
        print("save_as_file B")
        # self.needs_display_update = True
        #self.consolemsg("[Save As: ]" + f'{userinput}.txt')

    # def set_gmail_id(self, userinput):
    #     try:
    #         GmailCredentials.write_gmail_username(userinput)
    #         self.populate_gmail_menu()
    #         time.sleep(delay)
    #         self.menu.display()
    #     except Exception as e:
    #         print(e)

    # def set_gmail_pass(self, userinput):
    #     try:
    #         GmailCredentials.write_gmail_password(userinput)
    #         self.populate_gmail_menu()
    #         time.sleep(delay)
    #         self.menu.display()
    #     except Exception as e:
    #         print(e)

    def handle_key_press(self, e):
        self.reset_inactivity_timer()
        # debugging to see what these vars actually do (hint: they didn't work like how I expected them to)
        # print ("display update" + str(self.last_display_update))
        # print ("input update" + str(self.typing_last_time))
        # print ("Disp" + str(time.time()-self.last_display_update))
        # print ("Type" + str(time.time()-self.typing_last_time))
        # print("handle_key_press")
        # global break_loop_flag
        # break_loop_flag = True
        # print ("break_loop_flag: " + str(break_loop_flag))

        # print("KP Needs display update: " + str(self.needs_display_update))

        #debugging for lastAction
        # print ("lastAction: " + str(time.time()-lastAction))
        if self.input_mode:
            # print("input mode: " + str(self.input_mode))
            # print("screensaver mode: "+ str(self.screensaver_mode))
            if e.name == 'ctrl': #if control is pressed
                self.control_active = True
                print ("ctrl is pressed")
                return
            if e.name == 'shift': #if shift is pressed
                self.shift_active = True
                print ("shift is pressed")
                return

            if self.menu.inputMode:
                if len(e.name)==1:
                    if self.shift_active:
                        char = keymaps.shift_mapping.get(e.name)
                        self.menu.input_content += char
                    else:
                        self.menu.input_content += e.name
                if e.name=="backspace":
                    self.menu.input_content = self.menu.input_content[:-1]
                if e.name== "m" and self.control_active: #ctrl+m shows the menu
                    self.menu.input_content = ""
                    time.sleep(delay*3)
                    self.menu.display()
                    self.menu.cleanupInput()
                if e.name=="enter" and self.menu.input_content!="": #handle callback menu items
                    self.menu.menu_items[self.menu.selected_item]['callback']()
                    self.menu.cleanupInput()
                return

            if self.menu_mode:                
                if e.name == "w" or e.name == "up" or e.name == "left":
                    self.menu.up()
                elif e.name == "s" or e.name == "down" or e.name == "right":
                    self.menu.down()
                elif e.name == "enter":
                    self.menu.select()
                elif e.name == "q" and self.control_active:
                    self.exit()
                elif e.name == "esc":
                    self.hide_menu()
                    # print("hide_menu esc")
                elif e.name=="backspace" and self.menu==self.load_menu and self.control_active:
                    self.move_to_archive()
                elif e.name == "r" and self.control_active: #ctrl+r slow refresh
                    self.epd.init()
                    self.epd.Clear()
                    self.menu.display()
                elif e.name == "m" and self.control_active: #ctrl+m menu
                    self.hide_menu()
                    # print("hide_menu m")
                return
            
            if e.name == "esc":
                self.show_file_sample_menu()

            if e.name== "down" or e.name== "right" and self.display_updating==False:
                self.scrollindex = self.scrollindex - 1
                if self.scrollindex < 1:
                    self.scrollindex = 1
                self.consolemsg(f'[{round(len(self.previous_lines)/self.lines_on_screen)-self.scrollindex+1}/{round(len(self.previous_lines)/self.lines_on_screen)}]')
                self.needs_display_update = True
            time.sleep(delay)
            

            if e.name== "up" or e.name== "left" and self.display_updating==False:
                self.scrollindex = self.scrollindex + 1
                if self.scrollindex > round(len(self.previous_lines)/self.lines_on_screen+1):
                    self.scrollindex = round(len(self.previous_lines)/self.lines_on_screen+1)
                self.consolemsg(f'[{round(len(self.previous_lines)/self.lines_on_screen)-self.scrollindex+1}/{round(len(self.previous_lines)/self.lines_on_screen)}]')
                self.needs_display_update = True
                time.sleep(delay)


            #shortcuts:
            # if e.name == "m" and self.control_active: #ctrl+m menu
                # self.show_menu()
            if e.name == "s" and self.control_active: #ctrl+s quicksave file
                self.save_file()
                return
            if e.name == "n" and self.control_active: #ctrl+n new file
                self.new_file()
                return
            if e.name == "i" and self.control_active: #ctrl+i goes to the screen saver
                self.show_screensaver()
                return
            if e.name == "m" and self.control_active: #ctrl+m menu
                # self.menu_mode = True
                print("ctrl m")
                self.show_menu()
                return
                # self.menu.display()
            # if e.name == "q" and self.control_active: #ctrl+q qrcode
                # self.display_qr_code()
            # if e.name == "g" and self.control_active: #ctrl+g gmail
                # self.gmail_send()
            if e.name == "r" and self.control_active: #ctrl+r slow refresh
                self.doReset = True
                return
            if e.name == "backspace" and self.control_active: #ctrl+backspace delete prev word
                self.delete_previous_word()
            if e.name == "q" and self.control_active: #ctrl+q quit
                self.power_down(debug=False)
                return

            if e.name == "tab": 
                self.insert_character(" ")
                self.insert_character(" ")
                # Check if adding the character exceeds the line length limit
                if self.cursor_position > self.chars_per_line:
                    self.previous_lines.append(self.input_content)                
                    # Update input_content to contain the remaining characters
                    self.input_content = ""
                    self.needs_display_update = True #trigger a display refresh
                # Update cursor_position to the length of the remaining input_content
                self.cursor_position = len(self.input_content)
                # self.needs_input_update = True
                
            if e.name == "backspace":
                self.delete_character()
                # self.needs_input_update = True
                    
            elif e.name == "space": #space bar
                self.insert_character(" ")
                
                # Check if adding the character exceeds the line length limit
                if self.cursor_position > self.chars_per_line:
                    self.previous_lines.append(self.input_content)                
                    self.input_content = ""
                    self.needs_display_update = True
                # Update cursor_position to the length of the remaining input_content
                self.cursor_position = len(self.input_content)
                # self.needs_input_update = True
            
            elif e.name == "enter":
                if self.scrollindex>1:
                    #if you were reviewing text, jump to scrollindex=1
                    self.scrollindex = 1
                    time.sleep(delay)
                    self.update_display()
                    time.sleep(delay)
                    
                else:
                    # Add the input to the previous_lines array
                    self.previous_lines.append(self.input_content)
                    self.input_content = "" #clears input content
                    self.cursor_position=0
                    #save the file when enter is pressed
                    self.save_previous_lines(self.cache_file_path, self.previous_lines)
                    self.needs_display_update = True
                
            elif len(e.name) == 1 and self.control_active == False:  # letter and number input
                if self.shift_active:
                    # print(str(e.name)) #prints the name of the key that's pressed
                    char = keymaps.shift_mapping.get(e.name)
                    self.input_content += char
                else:
                    # print(str(e.name)) #prints the name of the key that's pressed
                    self.input_content += e.name

                self.cursor_position += 1
                # self.needs_input_update = True

                # Check if adding the character exceeds the line length limit
                if self.cursor_position > self.chars_per_line:
                    # Find the last space character before the line length limit
                    last_space = self.input_content.rfind(' ', 0, self.chars_per_line)
                    if last_space >= 0:
                        sentence = self.input_content[:last_space]
                        # Append the sentence to the previous lines
                        self.previous_lines.append(sentence)

                        # Update input_content to contain the remaining characters
                        self.input_content = self.input_content[last_space + 1:]
                        self.needs_display_update=True
                        # self.save_previous_lines()
                    else:
                        #There are no spaces in this line so input should move to next line
                        self.previous_lines.append(self.input_content[0:self.chars_per_line])
                        temp = self.input_content[-1]
                        self.input_content = temp
                        self.needs_display_update=True
                        # self.save_previous_lines()

                # Update cursor_position to the length of the remaining input_content
                self.cursor_position = len(self.input_content)
            
            #Ensure the input mode update is processed
            # if self.needs_input_update and not self.updating_input_area:
                # self.update_input_area()
                
            self.typing_last_time = time.time()
            # self.needs_input_update = True

        if not self.input_mode and self.screensaver_active:
            if e.name == "space": #Check the spacebar press to skip pause
                print("space")
                self.skip_pause = True
                return
            self.hide_screensaver()
            return
            # print("key is pressed")

    def reset_inactivity_timer(self):
        if self.inactivity_timer is not None:
            self.inactivity_timer.cancel()
        self.inactivity_timer = threading.Timer(self.inactivity_timeout, self.show_screensaver)
        self.inactivity_timer.start()

    def stop_inactivity_timer(self): #method to stop the inactivity timer
        if self.inactivity_timer is not None:
            self.inactivity_timer.cancel()
            self.inactivity_timer = None

    def handle_interrupt(self, signal, frame):
      self.keyboard.unhook_all()
      self.epd.init()
      self.epd.Clear()
      exit(0)

    def exit(self):
      self.keyboard.unhook_all()
      self.epd.init()
      self.epd.Clear()
      exit(0)
      
    def loop(self):

        if self.doReset:
            self.epd.init()
            self.epd.Clear()
            self.update_display()
            time.sleep(.5)
            self.update_input_area()
            self.doReset = False

        if self.menu.inputMode and not self.menu.screenupdating:
            self.menu.partial_update()

        elif self.needs_display_update and not self.display_updating:
            self.update_display()
            # self.update_input_area()
            # print("A")
            time.sleep(delay*2) #*2?
            self.typing_last_time = time.time()

        elif (time.time()-self.typing_last_time)<(.6):
            if not self.updating_input_area and not self.menu_mode and not self.screensaver_mode and self.scrollindex==1:
                self.update_input_area()
                # print("B")

    def run(self):
        self.load_file_into_previous_lines("cache.txt")
        self.previous_lines.clear()
        self.reset_inactivity_timer()
        while True:
            self.loop()
            # This small sleep prevents zerowriter from consuming 100% cpu
            # This does not negatively affect input delay
            time.sleep(0.01)
