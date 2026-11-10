"""Tắt / bật tiếng riêng một chương trình (vd mGBA) trong bộ trộn âm thanh Windows (như bấm loa trong Volume Mixer).
Dùng Windows Core Audio qua ctypes (không cần cài thêm gói): thiết bị phát mặc định -> các phiên âm thanh ->
phiên của tiến trình có tên exe khớp -> ISimpleAudioVolume.SetMute."""
import ctypes
from ctypes import wintypes, POINTER, byref, c_void_p, c_int, c_float

ole32 = ctypes.OleDLL('ole32')
k32 = ctypes.windll.kernel32
HRESULT = ctypes.HRESULT


class GUID(ctypes.Structure):
    _fields_ = [('a', wintypes.DWORD), ('b', wintypes.WORD), ('c', wintypes.WORD), ('d', ctypes.c_ubyte * 8)]

    def __init__(self, s):
        super().__init__()
        ole32.CLSIDFromString(ctypes.c_wchar_p('{%s}' % s), byref(self))


CLSID_MMDeviceEnumerator = GUID('BCDE0395-E52F-467C-8E3D-C4579291692E')
IID_IMMDeviceEnumerator = GUID('A95664D2-9614-4F35-A746-DE8DB63617E6')
IID_IAudioSessionManager2 = GUID('77AA99A0-1BD6-484F-8BC7-2C654C9A9B6F')
IID_IAudioSessionControl2 = GUID('BFB7FF88-7239-4FC9-8FA2-07C950BE9C6D')
IID_ISimpleAudioVolume = GUID('87CE5498-68D6-44E5-9215-6DA47EF883D8')


def _call(obj, idx, *args):
    """Gọi phương thức số idx trong vtable của đối tượng COM obj (c_void_p); args = [(kiểu, giá trị)]."""
    vt = ctypes.cast(obj, POINTER(POINTER(c_void_p)))[0]
    fn = ctypes.WINFUNCTYPE(HRESULT, c_void_p, *[t for t, _ in args])(vt[idx])
    return fn(obj, *[v for _, v in args])


def _release(obj):
    if obj:
        vt = ctypes.cast(obj, POINTER(POINTER(c_void_p)))[0]
        ctypes.WINFUNCTYPE(ctypes.c_ulong, c_void_p)(vt[2])(obj)


def _exe(pid):
    h = k32.OpenProcess(0x1000, False, pid)                   # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return ''
    try:
        buf, n = ctypes.create_unicode_buffer(260), wintypes.DWORD(260)
        k32.QueryFullProcessImageNameW(h, 0, buf, byref(n))
        return buf.value.lower()
    finally:
        k32.CloseHandle(h)


def _volumes(exe):
    """[ISimpleAudioVolume] mọi phiên âm thanh của tiến trình exe trên thiết bị phát mặc định (người gọi phải _release)."""
    try:
        ole32.CoInitializeEx(None, 2)                          # COINIT_APARTMENTTHREADED (đã khởi tạo rồi cũng không sao)
    except OSError:
        pass
    out, enum, dev, mgr, sess = [], c_void_p(), c_void_p(), c_void_p(), c_void_p()
    try:
        ole32.CoCreateInstance(byref(CLSID_MMDeviceEnumerator), None, 1, byref(IID_IMMDeviceEnumerator), byref(enum))
        _call(enum, 4, (c_int, 0), (c_int, 1), (POINTER(c_void_p), byref(dev)))         # GetDefaultAudioEndpoint(eRender, eMultimedia)
        _call(dev, 3, (POINTER(GUID), byref(IID_IAudioSessionManager2)), (wintypes.DWORD, 23),
              (c_void_p, None), (POINTER(c_void_p), byref(mgr)))                       # Activate
        _call(mgr, 5, (POINTER(c_void_p), byref(sess)))                                # GetSessionEnumerator
        cnt = c_int()
        _call(sess, 3, (POINTER(c_int), byref(cnt)))
        for i in range(cnt.value):
            ctl, ctl2, vol, pid = c_void_p(), c_void_p(), c_void_p(), wintypes.DWORD()
            _call(sess, 4, (c_int, i), (POINTER(c_void_p), byref(ctl)))
            try:
                _call(ctl, 0, (POINTER(GUID), byref(IID_IAudioSessionControl2)), (POINTER(c_void_p), byref(ctl2)))
                _call(ctl2, 14, (POINTER(wintypes.DWORD), byref(pid)))                 # GetProcessId
                if pid.value and _exe(pid.value).endswith(exe):
                    _call(ctl, 0, (POINTER(GUID), byref(IID_ISimpleAudioVolume)), (POINTER(c_void_p), byref(vol)))
                    out.append(vol)
            except OSError:
                pass
            finally:
                _release(ctl2)
                _release(ctl)
    finally:
        for o in (sess, mgr, dev, enum):
            _release(o)
    return out


def set_mute(mute, exe='mgba.exe'):
    """Tắt (True) / bật (False) tiếng exe. Trả số phiên đã đổi (0 = chưa thấy chương trình đang phát tiếng)."""
    vols = _volumes(exe)
    try:
        for v in vols:
            _call(v, 5, (wintypes.BOOL, bool(mute)), (c_void_p, None))                 # SetMute
        return len(vols)
    finally:
        for v in vols:
            _release(v)


def get_mute(exe='mgba.exe'):
    """True/False theo phiên đầu tiên, None nếu không thấy."""
    vols = _volumes(exe)
    try:
        if not vols:
            return None
        b = wintypes.BOOL()
        _call(vols[0], 6, (POINTER(wintypes.BOOL), byref(b)))
        return bool(b.value)
    finally:
        for v in vols:
            _release(v)


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) > 1:
        print('đổi', set_mute(sys.argv[1] == 'on'), 'phiên')
    print('mGBA đang tắt tiếng:', get_mute())
