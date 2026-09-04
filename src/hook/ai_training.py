"""AI training primitives: parameters, losses, optimizers and sequential models."""
from __future__ import annotations
import math
class Parameter:
    def __init__(self,value):self.value=value;self.grad=0
    def zero_grad(self):self.grad=0
class Optimizer:
    def __init__(self,params,lr=.001):self.params=list(params);self.lr=lr
    def step(self):
        for p in self.params:p.value-=self.lr*p.grad
    def zero_grad(self):
        for p in self.params:p.zero_grad()
class SGD(Optimizer):pass
class Adam(Optimizer):
    def __init__(self,params,lr=.001,beta1=.9,beta2=.999,eps=1e-8):super().__init__(params,lr);self.b1=beta1;self.b2=beta2;self.eps=eps;self.t=0;self.m={id(p):0 for p in self.params};self.v={id(p):0 for p in self.params}
    def step(self):
        self.t+=1
        for p in self.params:
            k=id(p);self.m[k]=self.b1*self.m[k]+(1-self.b1)*p.grad;self.v[k]=self.b2*self.v[k]+(1-self.b2)*p.grad*p.grad
            mh=self.m[k]/(1-self.b1**self.t);vh=self.v[k]/(1-self.b2**self.t);p.value-=self.lr*mh/(math.sqrt(vh)+self.eps)
def mse(pred,target):
    xs=list(pred);ys=list(target);return sum((a-b)**2 for a,b in zip(xs,ys))/max(1,len(xs))
def binary_cross_entropy(pred,target,eps=1e-12):
    return -sum(y*math.log(max(eps,p))+(1-y)*math.log(max(eps,1-p)) for p,y in zip(pred,target))/max(1,len(pred))
class Dataset:
    def __init__(self,items):self.items=list(items)
    def __len__(self):return len(self.items)
    def batch(self,size):
        for i in range(0,len(self.items),size):yield self.items[i:i+size]
