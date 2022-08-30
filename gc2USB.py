import os
import platform
import usb.core
import usb.backend.libusb1 as usb


if 'Windows' in platform.architecture()[1]:
    os_ver = 'amd64'
    if '32' in platform.architecture()[0]:
        os_ver = 'x86'
    os.environ['PATH'] += os.getcwd() + os.pathsep
    os.environ['PATH'] += os.path.dirname(os.path.realpath(__file__)) + os.sep + 'libusb' + os.sep + os_ver + os.pathsep
import time
from ctypes import c_void_p, c_int


class GC2USB:

    def __init__(self, printf=print):
        self.printf = print
        self.running = False
        self.last_received_data_time = None
        self.dev = None
        self._wait_for_hmt = False

    @property
    def wait_for_hmt(self):
        return self._wait_for_hmt

    @wait_for_hmt.setter
    def wait_for_hmt(self, value):
        self._wait_for_hmt = value

    def __del__(self):
        self.disconnect()

    @staticmethod
    def get_gc2_value(block, identifier):
        try:
            return block.split(identifier + '=', 1)[1].split('\n', 1)[0].strip()
        except:
            return

    @staticmethod
    def parse_gc2_usb_text(block, output_dict={}):
        identifier_dict = {}
        identifier_dict['current_time'] = 'MSEC_SINCE_CONTACT'
        identifier_dict['ID'] = 'SHOT_ID'
        identifier_dict['ball_speed'] = 'SPEED_MPH'
        identifier_dict['horizontal_launch_angle'] = 'AZIMUTH_DEG'
        identifier_dict['launch_angle'] = 'ELEVATION_DEG'
        identifier_dict['total_spin'] = 'SPIN_RPM'
        identifier_dict['side_spin'] = 'SIDE_RPM'
        identifier_dict['back_spin'] = 'BACK_RPM'
        identifier_dict['hmt'] = 'HMT'
        identifier_dict['club_speed'] = 'CLUBSPEED_MPH'
        identifier_dict['swing_path'] = 'HPATH_DEG'
        identifier_dict['angle_of_attack'] = 'VPATH_DEG'
        identifier_dict['face_to_target'] = 'FACE_T_DEG'
        identifier_dict['lie'] = 'LIE_DEG'
        identifier_dict['dynamic_loft'] = 'LOFT_DEG'
        identifier_dict['horizontal_impact_location'] = 'HIMPACT_MM'
        identifier_dict['veritcal_impact_location'] = 'VIMPACT_MM'
        identifier_dict['f_axis'] = 'FAXIS_DEG'
        identifier_dict['closure_rate'] = 'CLOSING_RATE_DEGSEC'
        for key, identifier in identifier_dict.items():
            value = GC2USB.get_gc2_value(block, identifier)
            if value is not None:
                output_dict[key] = value

        if int(output_dict.get('back_spin', -1)) == 3500:
            if int(output_dict.get('side_spin', -1)) == 0:
                output_dict['ball_speed'] = 0.0
        return output_dict

    def connect(self, callback, serial_number=None, bt_addr=None):
        self.running = True
        backend = usb.get_backend(find_library=(lambda x: 'libusb-1.0.dll'))
        if backend is None:
            print('Could not load USB Backend!')
            self.running = False
            return
        backend.lib.libusb_set_option.argtypes = [c_void_p, c_int]
        backend.lib.libusb_set_option(backend.ctx, 1)
        while self.running:
            try:
                print('Connecting to: USB GC2')
                self.dev = usb.core.find(idVendor=65535, idProduct=65535, backend=backend)
                if self.dev is None:
                    print('Alternate USB ID')
                    self.dev = usb.core.find(idVendor=11385, idProduct=272, backend=backend)
                if self.dev is None:
                    raise ValueError('GC2 not found')
                self.dev.set_configuration()
                cfg = self.dev.get_active_configuration()
                intf = cfg[(0, 0)]
                print('Connected GC2!')
                last_shot_id = -1
                self.running = True
                shot_dictionary = {}
                while self.running:
                    sret = None
                    try:
                        ret = self.dev.read(130, 10000, 100)
                        sret = ''.join([chr(x) for x in ret])
                    except KeyboardInterrupt:
                        break
                    except:
                        pass

                    self.last_received_data_time = time.time()
                    if sret:
                        try:
                            shot_dictionary = self.parse_gc2_usb_text(sret, output_dict=shot_dictionary)
                        except KeyError:
                            print('Could not parse: ' + sret)

                        if self._wait_for_hmt:
                            if shot_dictionary.get('hmt', '0') == '1':
                                continue
                        if last_shot_id:
                            if last_shot_id != shot_dictionary.get('ID', ''):
                                if float(shot_dictionary.get('ball_speed', 0.0)) > 0.01:
                                    if shot_dictionary.get('launch_angle', None) is not None:
                                        if callback:
                                            callback(shot_dictionary)
                        shot_dictionary = {}
                        last_shot_id = shot_dictionary.get('ID', -1)

            except (OSError, ValueError) as e:
                try:
                    print('Could not connect to GC2: ' + str(e))
                finally:
                    e = None
                    del e

            if self.dev:
                try:
                    usb.util.dispose_resources(self.dev)
                except OSError:
                    pass

                self.dev = None
            print('Disconnected GC2')
            if self.running:
                time.sleep(1.0)

    def disconnect(self):
        self.running = False

    def is_connected(self):
        if not self.running or self.dev is None:
            return False
        return True

    def is_running(self):
        return self.running

    def is_scanning(self):
        return False