"""Dependency-light AI primitives that form a stable HOOK model API."""
from __future__ import annotations
import math

class Tensor:
    def __init__(self,data): self.data=data
    def __repr__(self): return f"Tensor({self.data!r})"
    def map(self,fn): return Tensor(_map(self.data,fn))
    def __add__(self,other): return Tensor(_zip(self.data,other.data if isinstance(other,Tensor) else other,lambda a,b:a+b))
    def __mul__(self,other): return Tensor(_zip(self.data,other.data if isinstance(other,Tensor) else other,lambda a,b:a*b))

def _map(x,fn): return [_map(v,fn) for v in x] if isinstance(x,list) else fn(x)
def _zip(a,b,fn):
    if isinstance(a,list): return [_zip(x,b[i] if isinstance(b,list) else b,fn) for i,x in enumerate(a)]
    return fn(a,b)

def tensor(data): return Tensor(data)
def softmax(values):
    m=max(values); ex=[math.exp(x-m) for x in values]; s=sum(ex); return [x/s for x in ex]
def argmax(values): return max(range(len(values)),key=values.__getitem__)
def relu(x): return max(0,x)
def sigmoid(x): return 1/(1+math.exp(-x))
def linear(values,weights,bias=0): return sum(a*b for a,b in zip(values,weights))+bias

class Sequential:
    def __init__(self,*layers): self.layers=list(layers)
    def __call__(self,x):
        for layer in self.layers: x=layer(x)
        return x
    def add(self,layer): self.layers.append(layer); return self

class ModelRegistry:
    def __init__(self): self.models={}
    def register(self,name,model): self.models[name]=model; return model
    def get(self,name): return self.models[name]
    def predict(self,name,input): return self.models[name](input)
