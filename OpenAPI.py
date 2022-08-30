import json, os, random, re, socket, sys, threading, time, math
import win32.lib.win32con as win32con
import usb.core
from usb.backend import libusb1


class OpenAPI:

    def __init__(self, server_ip=None, buffer_size=1024):
        self.stay_connected = True
        self.s = None
        self.server_ip = server_ip
        self.buffer_size = buffer_size
        self.received_data = None
        self.last_received_data_time = None
        self.ball_launch_counter = 1
        self.config = {}
        self.read_config_file()
        if self.server_ip is None:
            self.server_ip = self.config.get('ip_address', 'localhost')
        self._club = 'DR'
        self._distance_to_flag = 0.0
        self._hand = 'right'
        self.recv_thread = threading.Thread(target=(self.recv_data_thread), daemon=True).start()

    def __del__(self):
        if self.s:
            self.s.close()

    def is_connected(self):
        if self.s is None:
            return False
        if self.last_received_data_time is None:
            return False
        return True

    def disconnect(self):
        self.stay_connected = False

    @property
    def club(self):
        return self._club

    @property
    def distance_to_flag(self):
        return self._distance_to_flag

    @property
    def hand(self):
        return self._hand

    def read_config_file(self):
        default_config = '[Config]\nIP=localhost'
        config_file_name = 'Config.txt'
        if os.path.isfile(config_file_name):
            with open(config_file_name, 'r', encoding="utf8", errors='ignore') as (config_file):
                for line in config_file:
                    if 'IP' in line:
                        self.config['ip_address'] = line[3:].rstrip()

        else:
            with open(config_file_name, 'w', encoding="utf8", errors='ignore') as (config_file):
                config_file.write(default_config)

    def print_game_info(self):
        print('Club: ' + self.club)
        print('Distance to Flag: ' + str(self.distance_to_flag))
        print('Hand: ' + self.hand)

    def parse_returned_data(self, ret_json):
        self._club = ret_json['data'].get('club_small', 'DR')
        self._distance_to_flag = float(ret_json['data'].get('distance_to_flag', 0.0))
        self._hand = ret_json['data'].get('handed_player', 'right')

    def recv_data_thread(self):
        while self.stay_connected:
            try:
                self.s = socket.create_connection((self.server_ip, 921), timeout=1.0)
                self.s.settimeout(2.0)
                while self.stay_connected:
                    try:
                        if self.last_received_data_time is not None:
                            if time.time() - self.last_received_data_time > 2.5:
                                self.last_received_data_time = None
                                break
                        if self.s:
                            data = self.s.recv(self.buffer_size)
                            if data:
                                data = data.decode('utf-8')
                                for d in data.splitlines():
                                    self.received_data = json.loads(d)
                                    self.parse_returned_data(self.received_data)
                                    self.last_received_data_time = time.time()

                    except json.decoder.JSONDecodeError:
                        print('Could not decode returned data')
                        print(str(data))
                    except (BlockingIOError, ConnectionAbortedError):
                        break

            except (socket.timeout, TimeoutError):
                print("Can't connect to OpenAPI")

            self.s = None

    def get_game_status(self):
        return self.received_data

    def launch_ball(self, ballspeed, ballpath, launchangle, backspin, sidespin, clubspeed=None, clubface=None, clubpath=None, sweetspot=None, drag=None, carry=None):
        try:
            totalspin = math.sqrt(float(sidespin) ^ 2 + str(backspin) ^ 2)
            spinaxis = math.atan(float(sidespin) / float(backspin)) * (180/math.pi)
            shot_json = json.loads('{"DeviceID":"gc2","Apiversion":"1","Units":"Yards","BallData":{"Speed":"0.0","SpinAxis":"0.0","TotalSpin":"0.0","HLA":"0.0","VLA":"0.0"},"ShotDataOptions":{"ContainsBallData":"true","ContainsClubData":"false","LaunchMonitorIsReady":"true","LaunchMonitorBallDetected":"true","IsHeartBeat":"false"}}')
            shot_json['BallData']['Speed'] = str(ballspeed)
            shot_json['BallData']['HLA'] = str(ballpath)
            shot_json['BallData']['VLA'] = str(launchangle)
            shot_json['BallData']['TotalSpin'] = str(totalspin)
            if self.hand == 'left':
                shot_json['data']['SpinAxis'] = str(-1.0 * float(spinaxis))
            else:
                shot_json['data']['SpinAxis'] = str(spinaxis)
            #if clubspeed:
            #    shot_json['data']['clubspeed'] = str(clubspeed)
            #if clubface:
            #    shot_json['data']['clubface'] = str(clubface)
            #if clubpath:
            #    shot_json['data']['clubpath'] = str(clubpath)
            #if sweetspot:
            #    shot_json['data']['sweetspot'] = str(sweetspot)
            #if drag is None:
            #    drag = 1.0
            #shot_json['data']['drag'] = str(drag)
            #if carry:
            #    shot_json['data']['carry'] = str(carry)
            if self.s:
                print(shot_json)
                self.s.send(json.dumps(shot_json, separators=(',', ':')).encode('utf-8'))
                return True
        except OSError:
            pass

        return False


if __name__ == '__main__':
    if len(sys.argv) == 1:
        gspro = OpenAPI()
    else:
        if len(sys.argv) == 2:
            gspro = OpenAPI(server_ip=(sys.argv[1]))
    last_shot_time = 0.0
    print('Starting random launches')
    while 1:
        time.sleep(0.1)
        dt = time.time() - last_shot_time
        if dt > 20.0:
            launch_status = gspro.launch_ball((random.uniform(20, 180)), (random.uniform(-7, 7)), (random.uniform(3, 45)), (random.uniform(1500, 10000)), (random.uniform(-2500, 2500)), clubspeed=(random.uniform(20, 120)),
                                              clubface=(random.uniform(-7, 7)),
                                              clubpath=(random.uniform(-7, 7)))
            if launch_status:
                print('New launch after ' + str(dt) + ' seconds.')
                last_shot_time = time.time()