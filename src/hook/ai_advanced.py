"""Dependency-free tensor, neural-network and transformer primitives for HOOK."""
from __future__ import annotations
import json, math, random
from pathlib import Path


def _shape(x):
    if not isinstance(x,list): return ()
    return (len(x),)+_shape(x[0]) if x else (0,)

def _flat(x):
    if isinstance(x,list):
        out=[]
        for v in x: out.extend(_flat(v))
        return out
    return [float(x)]

def _build(flat,shape):
    if not shape:return flat.pop(0)
    return [_build(flat,shape[1:]) for _ in range(shape[0])]

def _broadcast_shape(a,b):
    out=[]
    for x,y in zip(reversed(a),reversed(b)):
        if x==y or x==1: out.append(y)
        elif y==1: out.append(x)
        else: raise ValueError("incompatible tensor shapes")
    longer=a if len(a)>len(b) else b; out.extend(reversed(longer[:abs(len(a)-len(b))])); return tuple(reversed(out))

def _broadcast_to(data,shape):
    src=_shape(data)
    if src==shape:return data
    if len(src)>len(shape):raise ValueError("incompatible tensor shapes")
    padded=(1,)*(len(shape)-len(src))+src
    def expand(x,si):
        if si==len(shape):return x
        target=shape[si]; cur=padded[si]
        if si < len(shape)-len(src): x=[x]
        if cur==target:return [expand(v,si+1) for v in x]
        if cur==1:return [expand(x[0],si+1) for _ in range(target)]
        return [expand(v,si+1) for v in x]
    return expand(data,0)

class Tensor:
    def __init__(self,data,requires_grad=False):self.data=data if isinstance(data,list) else float(data);self.requires_grad=requires_grad;self.grad=None
    @property
    def shape(self):return _shape(self.data)
    @property
    def ndim(self):return len(self.shape)
    def clone(self):return Tensor(json.loads(json.dumps(self.data)),self.requires_grad)
    def flatten(self):return Tensor(_flat(self.data),self.requires_grad)
    def reshape(self,*shape):
        if math.prod(self.shape)!=math.prod(shape):raise ValueError("reshape changes tensor size")
        f=_flat(self.data);return Tensor(_build(f,list(shape)),self.requires_grad)
    def _binary(self,other,fn):
        b=other.data if isinstance(other,Tensor) else other; sa=self.shape; sb=_shape(b); shape=_broadcast_shape(sa,sb)
        aa=_flat(_broadcast_to(self.data,shape));bb=_flat(_broadcast_to(b,shape))
        return Tensor(_build([fn(x,y) for x,y in zip(aa,bb)],list(shape)),self.requires_grad or (isinstance(other,Tensor) and other.requires_grad))
    def __add__(self,o):return self._binary(o,lambda a,b:a+b)
    __radd__=__add__
    def __sub__(self,o):return self._binary(o,lambda a,b:a-b)
    def __rsub__(self,o):return Tensor(o)._binary(self,lambda a,b:a-b)
    def __mul__(self,o):return self._binary(o,lambda a,b:a*b)
    __rmul__=__mul__
    def __truediv__(self,o):return self._binary(o,lambda a,b:a/b)
    def matmul(self,other):
        a=self.data;b=other.data if isinstance(other,Tensor) else other
        if len(_shape(a))!=2 or len(_shape(b))!=2 or len(a[0])!=len(b):raise ValueError("matmul expects compatible 2D tensors")
        return Tensor([[sum(a[i][k]*b[k][j] for k in range(len(b))) for j in range(len(b[0]))] for i in range(len(a))])
    def sum(self):return sum(_flat(self.data))
    def mean(self):f=_flat(self.data);return sum(f)/max(1,len(f))
    def map(self,fn):return Tensor(_build([fn(v) for v in _flat(self.data)],list(self.shape)),self.requires_grad)
    def tolist(self):return self.data

class Parameter(Tensor):
    def __init__(self,data):super().__init__(data,True)

class Module:
    def parameters(self):
        out=[]
        for v in self.__dict__.values():
            if isinstance(v,Parameter):out.append(v)
            elif isinstance(v,Module):out.extend(v.parameters())
            elif isinstance(v,list):
                for x in v:
                    if isinstance(x,Module):out.extend(x.parameters())
                    elif isinstance(x,Parameter):out.append(x)
        return out
    def state_dict(self):
        out={}
        for k,v in self.__dict__.items():
            if isinstance(v,Parameter):out[k]=v.data
            elif isinstance(v,Module):
                for sk,sv in v.state_dict().items():out[f"{k}.{sk}"]=sv
            elif isinstance(v,list):
                for i,x in enumerate(v):
                    if isinstance(x,Module):
                        for sk,sv in x.state_dict().items():out[f"{k}.{i}.{sk}"]=sv
        return out
    def load_state_dict(self,state):
        for k,v in state.items():
            obj=self
            parts=k.split('.')
            for p in parts[:-1]:obj=obj[int(p)] if isinstance(obj,list) else getattr(obj,p)
            target= obj[int(parts[-1])] if isinstance(obj,list) else getattr(obj,parts[-1])
            target.data=v

class Linear(Module):
    def __init__(self,inputs,outputs,seed=0):
        r=random.Random(seed);scale=math.sqrt(2/max(1,inputs));self.weight=Parameter([[r.uniform(-scale,scale) for _ in range(inputs)] for _ in range(outputs)]);self.bias=Parameter([0.0]*outputs)
    def __call__(self,x):
        a=x.data if isinstance(x,Tensor) else x;return Tensor([sum(w*v for w,v in zip(row,a))+b for row,b in zip(self.weight.data,self.bias.data)])

class LayerNorm(Module):
    def __init__(self,size,eps=1e-5):self.weight=Parameter([1.0]*size);self.bias=Parameter([0.0]*size);self.eps=eps
    def __call__(self,x):
        rows=x.data if x.ndim==2 else [x.data];out=[]
        for row in rows:
            m=sum(row)/len(row);var=sum((v-m)**2 for v in row)/len(row);out.append([(v-m)/math.sqrt(var+self.eps)*w+b for v,w,b in zip(row,self.weight.data,self.bias.data)])
        return Tensor(out if x.ndim==2 else out[0])

class MultiHeadAttention(Module):
    def __init__(self,dim,heads=1,seed=0):
        if heads<1 or dim%heads:raise ValueError("embedding dimension must divide number of heads")
        self.dim=dim;self.heads=heads;self.q=Linear(dim,dim,seed);self.k=Linear(dim,dim,seed+1);self.v=Linear(dim,dim,seed+2);self.o=Linear(dim,dim,seed+3)
    def __call__(self,x):
        rows=x.data
        if _shape(rows)!=(len(rows),self.dim):raise ValueError("attention input must have shape [sequence, dim]")
        q=self.q(x).data;k=self.k(x).data;v=self.v(x).data;d=self.dim//self.heads;out=[[0.0]*self.dim for _ in rows]
        for h in range(self.heads):
            start=h*d;end=start+d
            for i in range(len(rows)):
                scores=[sum(q[i][start+z]*k[j][start+z] for z in range(d))/math.sqrt(d) for j in range(len(rows))]
                m=max(scores);ex=[math.exp(s-m) for s in scores];total=sum(ex);weights=[e/total for e in ex]
                for z in range(d):out[i][start+z]=sum(weights[j]*v[j][start+z] for j in range(len(rows)))
        return self.o(Tensor(out))

class FeedForward(Module):
    def __init__(self,dim,hidden,seed=0):self.a=Linear(dim,hidden,seed);self.b=Linear(hidden,dim,seed+1)
    def __call__(self,x):return self.b(self.a(x).map(lambda v:max(0.0,v)))

class TransformerBlock(Module):
    def __init__(self,dim,hidden,heads=1,seed=0):self.norm1=LayerNorm(dim);self.attn=MultiHeadAttention(dim,heads,seed);self.norm2=LayerNorm(dim);self.ff=FeedForward(dim,hidden,seed+10)
    def __call__(self,x):x=x+self.attn(self.norm1(x));return x+self.ff(self.norm2(x))

class TinyTransformer(Module):
    def __init__(self,vocab,dim=32,hidden=64,layers=2,heads=1,seed=0):
        r=random.Random(seed);self.vocab=vocab;self.dim=dim;self.embedding=Parameter([[r.uniform(-.1,.1) for _ in range(dim)] for _ in range(vocab)]);self.blocks=[TransformerBlock(dim,hidden,heads,seed+i*20) for i in range(layers)];self.output=Linear(dim,vocab,seed+100)
    def __call__(self,tokens):
        x=Tensor([self.embedding.data[int(t)] for t in tokens])
        for b in self.blocks:x=b(x)
        return self.output(x)
    def save(self,path):Path(path).write_text(json.dumps(self.state_dict()),encoding="utf-8")
    @classmethod
    def load(cls,path,**kwargs):obj=cls(**kwargs);obj.load_state_dict(json.loads(Path(path).read_text(encoding="utf-8")));return obj

class CharTokenizer:
    def __init__(self,text=""):self.vocab=sorted(set(text));self.to_id={c:i for i,c in enumerate(self.vocab)};self.from_id={i:c for c,i in self.to_id.items()}
    def encode(self,text):
        missing=[c for c in text if c not in self.to_id]
        if missing:raise ValueError(f"unknown token(s): {missing!r}")
        return [self.to_id[c] for c in text]
    def decode(self,tokens):return ''.join(self.from_id[int(t)] for t in tokens)

__all__=["Tensor","Parameter","Module","Linear","LayerNorm","MultiHeadAttention","FeedForward","TransformerBlock","TinyTransformer","CharTokenizer"]
