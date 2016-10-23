# coding:utf-8

from mini4wd.mabeee import MaBeee
from time import sleep

def _main():
    m=MaBeee()
    if not m.state()["state"]=="PoweredOn": return
    m.scan_start()
    if not m.scan()["scan"]: return
    dev_id=None
    while True:
        devs=m.devices()["devices"]
        for dev in devs:
            dev_id=dev["id"]
        if dev_id: break
    m.scan_stop()
    if not dev_id: return

    m.connect(dev_id)

    while True:
        if m.info(dev_id)["state"]=="Connected": break
        sleep(0.1)

    for n in range(10):
        m.set_pwm_duty(dev_id,(n+1)*10)
        sleep(1)
    m.set_pwm_duty(dev_id,0)

    return

if __name__ == "__main__" : _main()
