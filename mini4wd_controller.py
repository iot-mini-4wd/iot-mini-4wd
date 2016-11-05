# encoding : utf-8

import mini4wd.hid as hid
from mini4wd.mabeee import MaBeee
import struct
from time import sleep
import threading
from collections import namedtuple

class Mini4WDController(object):

    MABEEE_SEND_INTERVAL_SEC = 0.5
    SERVO_SEND_INTERVAL_SEC = 0.5

    def __init__(self, mabeee_url=None, handle_play=0):
        self.mabeee=MaBeee(mabeee_url)
        self.dev_id = None
        self.g27_bs = None
        self.handle_play = handle_play
        self.prev_speed = 0
        self.prev_handle = 0
        self.exit_flag = False

    def connect_mabeee(self):
        '''
        Connect to mabeee server.
        '''
        if not self.mabeee.state()["state"]=="PoweredOn": return None
        self.mabeee.scan_start()
        if not self.mabeee.scan()["scan"]: return None
        self.dev_id=None
        while True:
            devs=self.mabeee.devices()["devices"]
            for dev in devs:
                self.dev_id=dev["id"]
            if self.dev_id: break
        if not self.dev_id: return None

        self.mabeee.connect(self.dev_id)
        self.mabeee.scan_stop()

        while True:
            if self.mabeee.info(self.dev_id)["state"]=="Connected": break
            sleep(0.1)

    def convert_speed(self, bs, max=100):
        if not bs:
            return 0
        speed = 127 - ord(struct.unpack('c', bs[3:4])[0])
        if speed < 0:
            return 0
        elif speed > max:
            return max
        else:
            return speed

    def convert_handle(self, bs, min=-100, max=100, play=0):
        '''
        g27 wheel
          <-- left       right -->
        bs[0:2]
          0x0001            0xFF02
        convert to
          min    0(-play)  0(+play)     max
        '''
        if not bs:
            return 0
        handle = struct.unpack('h', bs[0:2] )[0] - 512
        if handle < play and handle > play * -1:
            return 0
        elif handle > max + play:
            return max
        elif handle < min - play:
            return min
        elif handle < 0:
            return handle + play
        else:
            return handle - play

    def convert_handle_button(self, bs):
        if not bs:
            return (False, False)
        b = ord(struct.unpack('c', bs[2:3])[0])
        HandleButton = namedtuple('HandleButton', ('left', 'right'))
        return HandleButton(b & 0b00000010 == 0b00000010, b & 0b00000001 == 0b00000001)

    def send_mabeee_server(self):
        '''
        Send G27 control to server.
        - speed to mabeee server
        '''
        speed = self.convert_speed(self.g27_bs)
        try:
            if self.prev_speed != speed:
                print 'S:%d' % (speed,)
                self.mabeee.set_pwm_duty(self.dev_id, speed)
                self.prev_speed = speed
        except Exception as e:
            print e
        if not self.exit_flag:
            t = threading.Timer(self.MABEEE_SEND_INTERVAL_SEC, self.send_mabeee_server)
            t.start()

    def send_servo(self):
        handle = self.convert_handle(self.g27_bs, play=self.handle_play)
        if self.prev_handle != handle:
            print 'H:%d' % (handle,)
            # !! send
            self.prev_handle = handle
        if not self.exit_flag:
            t = threading.Timer(self.SERVO_SEND_INTERVAL_SEC, self.send_servo)
            t.start()

    def start(self):
        '''
        from G27 device
        Send speed to mabeee server
        Send handle to servo
        if push right button on handle, exit controller
        '''
        # connect to mabeee server
        self.connect_mabeee()

        # find G27 device
        dev=None
        for d in hid.enumerate():
            if d['product_string'].startswith("G27"):
                dev=hid.Device(vid=d["vendor_id"],pid=d["product_id"])
                break
        if not dev:
            print 'G27 device not found.'
            return

        # Send to server at some interval.
        t_mabeee = threading.Timer(self.MABEEE_SEND_INTERVAL_SEC, self.send_mabeee_server)
        t_servo = threading.Timer(self.SERVO_SEND_INTERVAL_SEC, self.send_servo)
        t_mabeee.start()
        t_servo.start()

        # Read G27 device
        while True:
            self.g27_bs = dev.read(8)
            b = self.convert_handle_button(self.g27_bs)
            if b.right:
                self.exit_flag = True
                t_mabeee.cancel()
                t_servo.cancel()
                print 'exit'
                break

if __name__ == '__main__':
    controller = Mini4WDController(mabeee_url='http://localhost:8080', handle_play=50)
    controller.start()
