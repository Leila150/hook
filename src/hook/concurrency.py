"""Production-oriented concurrency primitives for HOOK."""
from __future__ import annotations
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from dataclasses import dataclass, field
from queue import Queue

class CancellationToken:
    def __init__(self): self._event=threading.Event()
    def cancel(self): self._event.set()
    @property
    def cancelled(self): return self._event.is_set()
    def throw_if_cancelled(self):
        if self.cancelled: raise asyncio.CancelledError()

class Channel:
    def __init__(self, capacity=0): self._q=Queue(maxsize=max(0,int(capacity)))
    def send(self,value): self._q.put(value); return value
    def receive(self): return self._q.get()
    def try_receive(self):
        try:return self._q.get_nowait()
        except Exception:return None

class TaskGroup:
    def __init__(self): self.tasks=[]
    async def __aenter__(self): return self
    async def __aexit__(self,exc_type,exc,tb):
        if exc:
            for t in self.tasks:t.cancel()
        results=await asyncio.gather(*self.tasks,return_exceptions=True)
        if exc:return False
        for r in results:
            if isinstance(r,BaseException):raise r
    def create_task(self,coro):
        t=asyncio.create_task(coro); self.tasks.append(t); return t

class Scheduler:
    def __init__(self): self._executor=ThreadPoolExecutor()
    def submit(self,fn,*args,**kwargs): return self._executor.submit(fn,*args,**kwargs)
    def map(self,fn,items): return list(self._executor.map(fn,items))
    def shutdown(self): self._executor.shutdown(wait=True)

@dataclass
class Mutex:
    _lock: threading.RLock=field(default_factory=threading.RLock)
    def acquire(self): return self._lock.acquire()
    def release(self): self._lock.release()
    def __enter__(self): self.acquire(); return self
    def __exit__(self,*_): self.release()

class Atom:
    def __init__(self,value=None): self._value=value; self._lock=threading.Lock()
    def get(self):
        with self._lock:return self._value
    def set(self,value):
        with self._lock:self._value=value
        return value
    def swap(self,fn):
        with self._lock:self._value=fn(self._value); return self._value
