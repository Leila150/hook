"""Native interoperability helpers for C, C++, Rust and platform libraries."""
from __future__ import annotations
import ctypes
from pathlib import Path

class NativeLibrary:
    def __init__(self,path): self.path=str(Path(path).expanduser()); self.handle=ctypes.CDLL(self.path)
    def function(self,name,restype=None,argtypes=None):
        fn=getattr(self.handle,name); fn.restype=restype
        if argtypes is not None: fn.argtypes=list(argtypes)
        return fn

class CInterop:
    load=staticmethod(lambda path: NativeLibrary(path))
    int8=ctypes.c_int8; int16=ctypes.c_int16; int32=ctypes.c_int32; int64=ctypes.c_int64
    uint8=ctypes.c_uint8; uint16=ctypes.c_uint16; uint32=ctypes.c_uint32; uint64=ctypes.c_uint64
    float32=ctypes.c_float; float64=ctypes.c_double; pointer=ctypes.POINTER; void_p=ctypes.c_void_p

class RustInterop(CInterop):
    """Rust cdylib/rlib consumers use the platform shared-library ABI."""
    pass

class CppInterop(CInterop):
    """C++ libraries must expose an extern-C ABI for direct symbol lookup."""
    pass

class ABI:
    C=CInterop; Cpp=CppInterop; Rust=RustInterop
