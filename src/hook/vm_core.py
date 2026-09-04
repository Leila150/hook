"""A real AST bytecode VM core used by the compiler roadmap."""
from __future__ import annotations
from dataclasses import dataclass
@dataclass(frozen=True)
class Op:
    code:str; arg:object=None
class Bytecode:
    def __init__(self,ops=()):self.ops=list(ops)
    def emit(self,code,arg=None):self.ops.append(Op(code,arg));return len(self.ops)-1
class VM:
    def __init__(self):self.stack=[];self.globals={};self.locals={};self.ip=0
    def run(self,program,globals_=None):
        if globals_ is not None:self.globals=globals_
        self.ip=0; self.stack=[]
        while self.ip<len(program.ops):
            op=program.ops[self.ip];self.ip+=1;c=op.code
            if c=='CONST':self.stack.append(op.arg)
            elif c=='LOAD':self.stack.append(self.locals.get(op.arg,self.globals[op.arg]))
            elif c=='STORE':self.globals[op.arg]=self.stack.pop()
            elif c=='POP':self.stack.pop()
            elif c=='ADD':b=self.stack.pop();a=self.stack.pop();self.stack.append(a+b)
            elif c=='SUB':b=self.stack.pop();a=self.stack.pop();self.stack.append(a-b)
            elif c=='MUL':b=self.stack.pop();a=self.stack.pop();self.stack.append(a*b)
            elif c=='DIV':b=self.stack.pop();a=self.stack.pop();self.stack.append(a/b)
            elif c=='RETURN':return self.stack.pop() if self.stack else None
            elif c=='JUMP':self.ip=int(op.arg)
            elif c=='JUMP_IF_FALSE':
                if not self.stack.pop():self.ip=int(op.arg)
            else:raise RuntimeError(f'unknown bytecode operation: {c}')
        return self.stack[-1] if self.stack else None
