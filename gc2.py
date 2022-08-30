from bluetooth import *  # Pybluez
import math, sys, time
from pyuac import runAsAdmin

class GC2:

    def __init__(self, printf=print):
        self.printf = print
        self.scanning = False
        self.running = False
        self.last_received_data_time = None
        self._wait_for_hmt = True

    @property
    def wait_for_hmt(self):
        return self._wait_for_hmt

    @wait_for_hmt.setter
    def wait_for_hmt(self, value):
        self._wait_for_hmt = value

    def __del__(self):
        self.disconnect()

    def scan(self):
        if self.scanning:
            raise RuntimeError('Already scanning')
        self.scanning = True
        output_list = []
        try:
            try:
                print('Scanning for GC2 Bluetooth Devices...')
                nearby_devices = discover_devices(duration=4, lookup_names=True, flush_cache=True, lookup_class=False)
                print('Found %d devices' % len(nearby_devices))
                for bt_addr, bt_name in nearby_devices:
                    try:
                        print('  %s - %s' % (bt_addr, bt_name))
                        if 'Foresight_GC2' in bt_name:
                            output_list.append((bt_addr, bt_name))
                    except UnicodeEncodeError:
                        print('  %s - %s' % (bt_addr, bt_name.encode('UTF-8', 'replace')))

            except:
                pass

        finally:
            self.scanning = False

        return output_list

    def get_bluetooth_address(self, serial_number):
        device_list = self.scan()
        for d in device_list:
            if str(serial_number) in d[1]:
                return d[0]

    @staticmethod
    def get_gc2_value(line, identifier):
        try:
            return line.split(identifier + '=', 1)[1].split(',', 1)[0]
        except:
            return

    @staticmethod
    def parse_gc2_string(line):
        identifier_dict = {}
        identifier_dict['current_time'] = 'CT'
        identifier_dict['serial_number'] = 'SN'
        identifier_dict['hardware_version'] = 'HW'
        identifier_dict['software_version'] = 'SW'
        identifier_dict['ID'] = 'ID'
        identifier_dict['shot_time'] = 'TM'
        identifier_dict['ball_speed'] = 'SP'
        identifier_dict['horizontal_launch_angle'] = 'AZ'
        identifier_dict['launch_angle'] = 'EL'
        identifier_dict['total_spin'] = 'TS'
        identifier_dict['side_spin'] = 'SS'
        identifier_dict['back_spin'] = 'BS'
        identifier_dict['carry'] = 'CY'
        identifier_dict['total'] = 'TL'
        identifier_dict['hmt'] = 'HMT'
        identifier_dict['club_speed'] = 'CS'
        identifier_dict['swing_path'] = 'HP'
        identifier_dict['angle_of_attack'] = 'VP'
        identifier_dict['face_to_target'] = 'FC'
        identifier_dict['lie'] = 'LI'
        identifier_dict['dynamic_loft'] = 'LF'
        identifier_dict['horizontal_impact_location'] = 'HI'
        identifier_dict['veritcal_impact_location'] = 'VI'
        identifier_dict['f_axis'] = 'FA'
        identifier_dict['closure_rate'] = 'CR'
        output_dict = {}
        for key, identifier in identifier_dict.items():
            value = GC2.get_gc2_value(line, identifier)
            if value is not None:
                output_dict[key] = value

        return output_dict

    def connect(self, callback, bt_addr=None, serial_number=None):
        self.running = True
        if bt_addr is None:
            bt_addr = self.get_bluetooth_address(serial_number)
        runAsAdmin(cmdLine=(os.path.dirname(os.path.realpath(__file__)) + os.sep + 'btpair.exe', bt_addr))
        port = 1
        while self.running:
            try:
                print('Connecting to: ' + bt_addr)
                sock = BluetoothSocket(RFCOMM)
                sock.connect((bt_addr, port))
                sock.settimeout(10.0)
                print('Connected GC2!')
                line = ''
                last_shot_time = None
                self.running = True
                empty_message_count = 0
                while self.running:
                    data = sock.recv(1024)
                    if not data:
                        empty_message_count = empty_message_count + 1
                        if empty_message_count < 100:
                            continue
                        break
                    self.last_received_data_time = time.time()
                    line += data.decode('UTF-8')
                    if line:
                        if line[(-1)] == '\n':
                            shot_dictionary = None
                            for l in line.splitlines():
                                try:
                                    parsed = GC2.parse_gc2_string(l)
                                    if parsed:
                                        shot_dictionary = parsed
                                except KeyError:
                                    print('Could not parse: ' + line)

                            line = ''
                            if self._wait_for_hmt:
                                if shot_dictionary.get('hmt', '0') == '1':
                                    continue
                            if shot_dictionary is None:
                                continue
                            if last_shot_time and last_shot_time != shot_dictionary.get('shot_time', '') and float(shot_dictionary.get('ball_speed', 0.0)) > 0.01:
                                if callback:
                                    callback(shot_dictionary)
                        last_shot_time = shot_dictionary.get('shot_time', '')

            except OSError as e:
                try:
                    print('Could not connect to GC2: ' + str(e))
                finally:
                    e = None
                    del e

            sock.close()
            print('Disconnected GC2')
            if self.running:
                time.sleep(1.0)

    def disconnect(self):
        self.running = False

    def is_connected(self):
        if not self.running or self.last_received_data_time is None:
            return False
        return time.time() - self.last_received_data_time <= 4.0

    def is_running(self):
        return self.running

    def is_scanning(self):
        return self.scanning