# coding:utf-8
import requests
import json
from time import sleep
from urlparse import urljoin as join

class MaBeee(object):
    server_url_ = ""
    def __init__(self,url="http://localhost:11111"):
        MaBeee.server_url_ = url
        pass

    def _get(self,url,params=None):
        if params==None:
            r = requests.get(join(MaBeee.server_url_,url))
        else:
            r = requests.get(join(MaBeee.server_url_,url),params=params)
        if r.status_code!=200:
            raise Exception("_get status code error! %d"%(r.status_code,))
        if len(r.content)!=0:
            return json.loads(r.content)
        return None

    def summary(self):
        return self._get("")

    def state(self):
        return self._get("state")

    def scan(self):
        return self._get("scan")

    def scan_start(self):
        return self._get("scan/start")

    def scan_stop(self):
        return self._get("scan/stop")

    def devices(self):
        sleep(1)
        return self._get("devices")

    def info(self,id):
        return self._get("devices/%d"%id)

    def connect(self,id):
        sleep(1)
        return self._get("devices/%d/connect"%id)

    def disconnect(self,id):
        return self._get("devices/%d/disconnect"%id)

    def set_pwm_duty(self,id,pwm_duty):
        """
        pwm_duty:=0~100
        """
        payload={"pwm_duty":pwm_duty,}
        return self._get("devices/%d/set"%id,payload)

    def update(self,id,prop):
        """
        prop:=
        rssi/battery_voltage
        """
        payload={"p":prop,}
        return self._get("devices/%d/update"%id,payload)
