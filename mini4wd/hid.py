import ctypes
import atexit
import platform
import os

pfname=platform.system()
if pfname == "Windows":
    os.environ["PATH"]=os.environ["PATH"] + ";" + os.path.dirname(__file__)

__all__ = ['HIDException', 'DeviceInfo', 'Device', 'enumerate']


hidapi = None
library_paths = (
    'libhidapi-hidraw.so',
    'libhidapi-hidraw.so.0',
    'libhidapi-libusb.so',
    'libhidapi-libusb.so.0',
    'libhidapi-iohidmanager.so',
    'libhidapi-iohidmanager.so.0'
)

for lib in library_paths:
    try:
        hidapi = ctypes.cdll.LoadLibrary(lib)
        break
    except OSError:
        pass
else:
    try:
        if pfname=="Darwin":
            hidapi = ctypes.cdll.LoadLibrary('libhidapi.dylib')
        elif pfname=="Windows":
            hidapi = ctypes.cdll.LoadLibrary('hidapi.dll')
    except AttributeError:
        raise ImportError("Unable to load the HIDAPI library")


hidapi.hid_init()
atexit.register(hidapi.hid_exit)

hidapi.hid_open.restype = ctypes.c_void_p
hidapi.hid_open_path.restype = ctypes.c_void_p

hidapi.hid_get_manufacturer_string.restype = ctypes.c_int
hidapi.hid_get_manufacturer_string.argtypes = (ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_size_t)

hidapi.hid_get_product_string.restype = ctypes.c_int
hidapi.hid_get_product_string.argtypes = (ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_size_t)

hidapi.hid_get_serial_number_string.restype = ctypes.c_int
hidapi.hid_get_serial_number_string.argtypes = (ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_size_t)

hidapi.hid_read.restype = ctypes.c_int
hidapi.hid_read.argtypes = (ctypes.c_void_p,ctypes.c_char_p,ctypes.c_size_t)

hidapi.hid_read_timeout.restype = ctypes.c_int
hidapi.hid_read_timeout.argtypes = (ctypes.c_void_p,ctypes.c_char_p,ctypes.c_size_t,ctypes.c_int)


hidapi.hid_write.restype = ctypes.c_int
hidapi.hid_write.argtypes = (ctypes.c_void_p,ctypes.c_char_p,ctypes.c_size_t)

class HIDException(Exception):
    pass


class DeviceInfo(ctypes.Structure):
    def as_dict(self):
        ret = {}
        for name, type in self._fields_:
            if name == 'next':
                continue
            ret[name] = getattr(self, name, None)

        return ret

DeviceInfo._fields_ = [
    ('path', ctypes.c_char_p),
    ('vendor_id', ctypes.c_ushort),
    ('product_id', ctypes.c_ushort),
    ('serial_number', ctypes.c_wchar_p),
    ('release_number', ctypes.c_ushort),
    ('manufacturer_string', ctypes.c_wchar_p),
    ('product_string', ctypes.c_wchar_p),
    ('usage_page', ctypes.c_ushort),
    ('usage', ctypes.c_ushort),
    ('interface_number', ctypes.c_int),
    ('next', ctypes.POINTER(DeviceInfo)),
]

hidapi.hid_enumerate.restype = ctypes.POINTER(DeviceInfo)
hidapi.hid_error.restype = ctypes.c_wchar_p


def enumerate(vid=0, pid=0):
    ret = []
    info = hidapi.hid_enumerate(vid, pid)
    c = info

    while c:
        ret.append(c.contents.as_dict())
        c = c.contents.next

    hidapi.hid_free_enumeration(info)

    return ret


class Device(object):
    def __init__(self, vid=None, pid=None, serial=None, path=None):
        if path:
            self.__dev = hidapi.hid_open_path(path)
        elif serial:
            serial = ctypes.create_unicode_buffer(serial)
            self.__dev = hidapi.hid_open(vid, pid, serial)
        elif vid and pid:
            self.__dev = hidapi.hid_open(vid, pid, None)
        else:
            raise ValueError('specify vid/pid or path')

        if self.__dev == 0:
            raise HIDException('unable to open device')
        print self.__dev

    def __hidcall(self, function, *args, **kwargs):
        if self.__dev == 0:
            raise HIDException('device closed')

        ret = function(*args, **kwargs)
        if ret == -1:
            err = hidapi.hid_error(self.__dev)
            raise HIDException(err)
        return ret

    def __readstring(self, function, max_length=255):
        buf = ctypes.create_unicode_buffer(max_length)
        self.__hidcall(function, self.__dev, buf, max_length)
        return buf.value

    def write(self, data):
        return self.__hidcall(hidapi.hid_write, self.__dev, data, len(data))

    def read(self, size, timeout=None):
        data = ctypes.create_string_buffer(size)
        if timeout is None:
            size = self.__hidcall(hidapi.hid_read, self.__dev, data, size)
        else:
            size = self.__hidcall(
                hidapi.hid_read_timeout, self.__dev, data, size, timeout)

        return data.raw[:size]

    def send_feature_report(self, data):
        return self.__hidcall(hidapi.hid_send_feature_report,
                              self.__dev, data, len(data))

    def get_feature_report(self, report_id, size):
        data = ctypes.create_string_buffer(size)

        # Pass the id of the report to be read.
        data[0] = chr(report_id)

        size = self.__hidcall(
            hidapi.hid_get_feature_report, self.__dev, data, size)
        return data.raw[:size]

    def close(self):
        if self.__dev != 0:
            hidapi.hid_close(self.__dev)
            self.__dev = 0

    @property
    def nonblocking(self):
        return getattr(self, '_nonblocking', 0)

    @nonblocking.setter
    def nonblocking(self, value):
        self.__hidcall(hidapi.hid_set_nonblocking, self.__dev, value)
        setattr(self, '_nonblocking', value)

    @property
    def manufacturer(self):
        return self.__readstring(hidapi.hid_get_manufacturer_string)

    @property
    def product(self):
        return self.__readstring(hidapi.hid_get_product_string)

    @property
    def serial(self):
        return self.__readstring(hidapi.hid_get_serial_number_string)

    def get_indexed_string(self, index, max_length=255):
        buf = ctypes.create_unicode_buffer(max_length)
        self.__hidcall(hidapi.hid_get_indexed_string,
                       self.__dev, index, buf, max_length)
        return buf.value
