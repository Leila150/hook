"""Memory, GC and unsafe/native primitives exposed as a small stable API."""
from __future__ import annotations
import ctypes, gc
class Pointer:
    def __init__(self,address,ctype=ctypes.c_ubyte): self.address=int(address); self.ctype=ctype
    def read(self): return self.ctype.from_address(self.address).value
    def write(self,value): self.ctype.from_address(self.address).value=value; return value
    def offset(self,n): return Pointer(self.address+int(n)*ctypes.sizeof(self.ctype),self.ctype)
    def __int__(self): return self.address
class MemoryManager:
    def allocate(self,size): return ctypes.create_string_buffer(int(size))
    def pointer(self,obj): return Pointer(ctypes.addressof(obj))
    def sizeof(self,obj): return ctypes.sizeof(obj)
    def collect(self): return gc.collect()
    def enable_gc(self): gc.enable()
    def disable_gc(self): gc.disable()
    def stats(self): return {"threshold":gc.get_threshold(),"counts":gc.get_count()}
class Unsafe:
    enabled=True
    @staticmethod
    def cast(address,ctype): return ctype.from_address(int(address))
    @staticmethod
    def pointer(obj): return Pointer(ctypes.addressof(obj))
