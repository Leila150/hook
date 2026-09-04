"""Native ABI binding helpers with explicit ownership and symbol metadata."""
from __future__ import annotations
import ctypes
class Ownership:
    BORROWED='borrowed'; OWNED='owned'; SHARED='shared'
class Binding:
    def __init__(self,library,name,restype=None,argtypes=None,ownership=Ownership.BORROWED):
        self.library=library; self.name=name; self.ownership=ownership
        self.function=getattr(library,name); self.function.restype=restype
        if argtypes is not None:self.function.argtypes=argtypes
    def __call__(self,*args):return self.function(*args)
class NativeBindings:
    TYPES={n:getattr(ctypes,n) for n in ('c_bool','c_char','c_byte','c_ubyte','c_short','c_ushort','c_int','c_uint','c_long','c_ulong','c_longlong','c_ulonglong','c_float','c_double','c_void_p','c_char_p')}
    def load(self,path):return ctypes.CDLL(path)
    def bind(self,library,name,restype=None,argtypes=None,ownership='borrowed'):return Binding(library,name,restype,argtypes,ownership)
    def sizeof(self,t):return ctypes.sizeof(t)
    def callback(self,restype,argtypes):return ctypes.CFUNCTYPE(restype,*argtypes)
