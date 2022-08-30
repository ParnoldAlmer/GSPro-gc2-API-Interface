from functools import partial
import os, subprocess, threading, time, tkinter as tk
from gc2 import GC2
from gc2USB import GC2USB
from OpenAPI import OpenAPI
from pyuac import runAsAdmin


GC2_GUI_VERSION = '1.1'
root = tk.Tk()
root.geometry('400x200')
root.title('OpenAPI GC2 Interface ' + GC2_GUI_VERSION)
g = GC2()
u = GC2USB()
p = OpenAPI()
saved_file_name = 'lastgc2.txt'
saved_serial = ''
saved_addr = '127.0.0.1'
try:
    with open('lastgc2.txt', 'r', encoding="utf-8", errors='ignore') as (saved_gc2):
        f = saved_gc2.read().splitlines()
        if len(f) == 2:
            saved_serial = f[0]
            saved_addr = f[1]
except FileNotFoundError:
    pass

gc2_mac_address_dict = {}


def validateGC2Serial(action_type, index, value, previous, new_text, validation_types, validation_type, widget_name):
    try:
        if value is '':
            return True
        int(value)
    except:
        return False
        return True


class GC2ScanTask(threading.Thread):

    def __init__(self, gc2, root, listbox):
        threading.Thread.__init__(self)
        self.root = root
        self.listbox = listbox
        self.gc2 = gc2

    def run(self):
        self.listbox.delete(0, tk.END)
        try:
            list_of_devices = g.scan()
        except RuntimeError:
            return
        else:
            for d in list_of_devices:
                self.listbox.insert(tk.END, str(d[1]))
                gc2_mac_address_dict[d[1]] = d[0]


class GC2ConnectTask(threading.Thread):

    def __init__(self, gc2, gspro, serial_number=None, bt_addr=None):
        threading.Thread.__init__(self)
        self.gc2 = gc2
        self.gspro = gspro
        self.serial = serial_number
        self.bt_addr = bt_addr

    def __del__(self):
        self.gc2.disconnect()

    def run(self):
        if not self.gc2.is_connected():
            try:
                os.remove('lastgc2.txt')
            except FileNotFoundError:
                pass

            try:
                with open('lastgc2.txt', 'w', encoding="utf8", errors='ignore') as (saved_gc2):
                    saved_gc2.write(str(self.serial) + '\n')
                    if self.bt_addr:
                        saved_gc2.write(str(self.bt_addr))
            except FileNotFoundError:
                pass

            subprocess.check_call(['attrib', '+H', 'lastgc2.txt'])
            self.gc2.connect((self.cb), serial_number=(self.serial), bt_addr=(self.bt_addr))
        else:
            print('Gc2 already connected?')

    def cb(self, l):
        clubpath = l.get('swing_path', None)
        if clubpath is not None:
            try:
                clubpath = -1.0 * float(clubpath)
            except:
                pass

        face_to_path = None
        face_to_target = l.get('face_to_target', None)
        if face_to_target is not None:
            if clubpath is not None:
                try:
                    face_to_path = -1.0 * float(face_to_target) - clubpath
                except:
                    pass

        if l.get('back_spin', 0.0) == 0.0:
            if l.get('side_spin', 0.0) == 0.0:
                print('Rejecting shot due to zero total spin, assumed misread.')
                return
        if l.get('back_spin', 0.0) == 2222.0:
            print('Rejecting shot due 2222 backspin, assumed misread.')
            return
        self.gspro.launch_ball((l.get('ball_speed', 0.0)), (l.get('horizontal_launch_angle', 0.0)), (l.get('launch_angle', 0.0)), (l.get('back_spin', 0.0)), (l.get('side_spin', 0.0)), clubspeed=(l.get('club_speed', None)),
                               clubface=face_to_path,
                               clubpath=clubpath,
                               sweetspot=(l.get('horizontal_impact_location', None)))


def scanForGC2s(listbox):
    GC2ScanTask(g, root, listbox).start()


def onSelect(serial_entry, evt):
    try:
        w = evt.widget
        index = int(w.curselection()[0])
        value = w.get(index)
        print('You selected item %d: "%s"' % (index, value))
        serial_entry.delete(0, tk.END)
        serial_entry.insert(0, value[14:])
    except IndexError:
        pass


def setWaitForHMT(wait_for_hmt_var):
    if wait_for_hmt_var.get():
        g.wait_for_hmt = True
    else:
        g.wait_for_hmt = False


def connect(serial_entry):
    serial = serial_entry.get()
    bt_addr = None
    if serial == saved_serial:
        bt_addr = saved_addr
    for key, value in gc2_mac_address_dict.items():
        if key[14:] == serial:
            bt_addr = value

    GC2ConnectTask(g, p, serial, bt_addr=bt_addr).start()


def usb_connect():
    GC2ConnectTask(u, p).start()


def disconnect():
    g.disconnect()


def usb_disconnect():
    u.disconnect()


def on_closing():
    disconnect()
    p.disconnect()
    root.destroy()


gc2_selection_frame = tk.Frame(root)
serial_frame = tk.Frame(gc2_selection_frame)
gc2_selected_var = tk.StringVar()
gc2_entry = tk.Entry(serial_frame, textvariable=gc2_selected_var, width=8, justify='left', validate='key')
connect_button = tk.Button(serial_frame, text='Connect Bluetooth')
usb_button = None

def drawConnectionStatus():
    if p.is_connected():
        protee_connected_indicator.configure(bg='sea green')
    else:
        protee_connected_indicator.configure(bg='red4')
    if g.is_scanning():
        gc2_connected_indicator.configure(bg='RoyalBlue3')
        connect_button.configure(text='Scanning', state=(tk.DISABLED))
    else:
        if g.is_connected():
            gc2_connected_indicator.configure(bg='sea green')
            connect_button.configure(text='Disconnect Bluetooth', state=(tk.NORMAL), command=disconnect)
        else:
            if g.is_running():
                gc2_connected_indicator.configure(bg='goldenrod1')
                connect_button.configure(text='Disconnect Bluetooth', state=(tk.NORMAL), command=disconnect)
            else:
                gc2_connected_indicator.configure(bg='red4')
                connect_button.configure(text='Connect Bluetooth', state=(tk.NORMAL), command=(partial(connect, gc2_entry)))
    if u.is_scanning():
        usb_connected_indicator.configure(bg='RoyalBlue3')
        usb_button.configure(text='Scanning', state=(tk.DISABLED))
    else:
        if u.is_connected():
            usb_connected_indicator.configure(bg='sea green')
            usb_button.configure(text='Disconnect USB', state=(tk.NORMAL), command=usb_disconnect)
        else:
            if u.is_running():
                usb_connected_indicator.configure(bg='goldenrod1')
                usb_button.configure(text='Disconnect USB', state=(tk.NORMAL), command=usb_disconnect)
            else:
                usb_connected_indicator.configure(bg='red4')
                usb_button.configure(text='Connect USB', state=(tk.NORMAL), command=usb_connect)
    root.after(500, drawConnectionStatus)


tk.Label(serial_frame, text='Selected GC2 Serial (Number Only)').pack(side=(tk.LEFT))
gc2_entry['validatecommand'] = (gc2_entry.register(validateGC2Serial), '%d', '%i', '%P', '%s', '%S', '%v', '%V', '%W')
gc2_entry.insert(0, saved_serial)
gc2_entry.pack(side=(tk.LEFT))
connect_button.pack(side=(tk.LEFT), padx=5)
serial_frame.pack(side=(tk.TOP), fill=(tk.X))
gc2_button_frame = tk.Frame(gc2_selection_frame)
scan_button = tk.Button(gc2_button_frame, text='Scan for GC2s')
scan_button.pack(side=(tk.LEFT))
gc2_button_frame.pack(anchor=(tk.W), pady=10)
body_frame = tk.Frame(gc2_selection_frame)
gc2_list_frame = tk.Frame(body_frame)
gc2_list = tk.Listbox(gc2_list_frame, height=5, selectmode=(tk.SINGLE))
gc2_list.bind('<<ListboxSelect>>', partial(onSelect, gc2_entry))
gc2_list.pack(side=(tk.LEFT))
scrollbar = tk.Scrollbar(gc2_list_frame, orient='vertical')
scrollbar.config(command=(gc2_list.yview))
scrollbar.pack(side=(tk.RIGHT), fill=(tk.Y))
gc2_list.config(yscrollcommand=(scrollbar.set))
gc2_list_frame.pack(side=(tk.LEFT), anchor=(tk.N))
options_frame = tk.Frame(body_frame)
wait_for_hmt = tk.BooleanVar()
waitForHMTCheck = tk.Checkbutton(options_frame, text='Wait for HMT', variable=wait_for_hmt)
waitForHMTCheck['command'] = partial(setWaitForHMT, wait_for_hmt)
waitForHMTCheck.deselect()
g.wait_for_hmt = False
waitForHMTCheck.pack(side=(tk.TOP))
options_frame.pack(side=(tk.LEFT), anchor=(tk.N), fill=(tk.X))
usb_button = tk.Button(body_frame, text='Connect USB')
usb_button.pack(side=(tk.RIGHT), anchor=(tk.S), padx=10)
body_frame.pack(side=(tk.TOP), fill=(tk.X), anchor=(tk.W))
scan_button.configure(command=(partial(scanForGC2s, gc2_list)))
gc2_selection_frame.pack(side=(tk.TOP), fill=(tk.X))
connection_status_frame = tk.Frame(root)
tk.Label(connection_status_frame, text='OpenAPI').pack(side=(tk.LEFT))
protee_connected_indicator = tk.Frame(connection_status_frame, bg='red4')
protee_connected_indicator.pack(side=(tk.LEFT), ipadx=7, ipady=7, padx=5)
tk.Label(connection_status_frame, text='\tGC2 Bluetooth').pack(side=(tk.LEFT))
gc2_connected_indicator = tk.Frame(connection_status_frame, bg='red4')
gc2_connected_indicator.pack(side=(tk.LEFT), ipadx=7, ipady=7, padx=5)
tk.Label(connection_status_frame, text='\tGC2 USB').pack(side=(tk.LEFT))
usb_connected_indicator = tk.Frame(connection_status_frame, bg='red4')
usb_connected_indicator.pack(side=(tk.LEFT), ipadx=7, ipady=7, padx=5)
connection_status_frame.pack(side=(tk.BOTTOM), fill=(tk.X))
drawConnectionStatus()
root.protocol('WM_DELETE_WINDOW', on_closing)
try:
    root.mainloop()
except KeyboardInterrupt:
    on_closing()