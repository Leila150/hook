"""HOOK v0.1 execution engine."""
from __future__ import annotations
import re
from dataclasses import dataclass
from pathlib import Path
from .errors import *

@dataclass
class Token:
    kind:str; value:str; line:int; column:int
    def __str__(self): return self.value or self.kind
    __repr__ = __str__

class Lexer:
    def __init__(self,source): self.source=source
    def tokenize(self):
        out=[]; stack=[0]
        pat=re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|\b\d+(?:\.\d+)?\b|[A-Za-z_]\w*|==|!=|<=|>=|\*\*|//|<<|>>|\?\?|!<=|!>=|!<|!>|[+\-*/%&|^~<>=(),.\[\]{}:`]')
        lines=self.source.splitlines()
        for no,raw in enumerate(lines,1):
            if not raw.strip() or raw.lstrip().startswith(("#","--")): continue
            n=len(raw)-len(raw.lstrip(' '))
            if '\t' in raw[:n]: raise SyntaxError('tabs are not allowed; use spaces',no)
            if n>stack[-1]: stack.append(n); out.append(Token('INDENT','',no,1))
            while n<stack[-1]: stack.pop(); out.append(Token('DEDENT','',no,1))
            if n!=stack[-1]: raise SyntaxError('inconsistent indentation',no)
            for m in pat.finditer(raw[n:]):
                v=m.group(); kind='STRING' if v[0] in "\"'" else ('NUMBER' if v[0].isdigit() else ('IDENT' if v[0].isalpha() or v[0]=='_' else 'OP'))
                out.append(Token(kind,v,no,n+m.start()+1))
            out.append(Token('NEWLINE','',no,len(raw)+1))
        while len(stack)>1: stack.pop(); out.append(Token('DEDENT','',len(lines)+1,1))
        out.append(Token('EOF','',len(lines)+1,1)); return out

@dataclass
class Node:
    text:str; line:int; indent:int; children:list
    def __repr__(self): return f"Node({self.text!r}, line={self.line})"

def _type_display(value):
    if isinstance(value, HookType): return value.name
    if isinstance(value, HookErrorType): return value.name
    if isinstance(value, HookClass): return value.name
    if isinstance(value, HookFunction): return f"function {value.name}"
    if isinstance(value, HookObject): return f"{value.cls.name} object"
    if isinstance(value, Token): return f"Token({value.kind}, {value.value!r})"
    return type(value).__name__

def hook_repr(value):
    """Return the canonical human-readable representation of any HOOK value."""
    if isinstance(value, HookType): return value.name
    if isinstance(value, HookErrorType): return value.name
    if isinstance(value, HookClass): return f"class {value.name}"
    if isinstance(value, HookFunction): return f"function {value.name}"
    if isinstance(value, HookObject): return f"<{value.cls.name} object>"
    if isinstance(value, HookError): return str(value)
    if value is None: return "None"
    if isinstance(value, bool): return "True" if value else "False"
    if isinstance(value, str): return value
    if isinstance(value, list): return "[" + ", ".join(hook_repr(v) for v in value) + "]"
    if isinstance(value, tuple): return "(" + ", ".join(hook_repr(v) for v in value) + ("," if len(value)==1 else "") + ")"
    if isinstance(value, dict): return "{" + ", ".join(f"{hook_repr(k)}: {hook_repr(v)}" for k,v in value.items()) + "}"
    if isinstance(value, Token): return f"Token({value.kind}, {value.value!r})"
    return str(value)

def hook_print(*values, sep=" ", end="\n"):
    print(sep.join(hook_repr(v) for v in values), end=end)

class HookType:
    """A printable HOOK language type descriptor."""
    def __init__(self,name,converter=None): self.name=name; self.converter=converter
    def __str__(self): return self.name
    def __repr__(self): return self.name
    def __call__(self,*args):
        if self.converter is None: return self
        if len(args)!=1: raise TypeError(f"{self.name} conversion expects one value")
        return self.converter(args[0])

class HookErrorType(HookType):
    """Printable error type which can also construct the corresponding HOOK error."""
    def __init__(self,name,error_cls): super().__init__(name); self.error_cls=error_cls
    def __call__(self,message="",*args,**kwargs): return self.error_cls(message,*args,**kwargs)

class Parser:
    def __init__(self,source):
        self.source=source; self.lines=[]
        for no,raw in enumerate(source.splitlines(),1):
            if not raw.strip() or raw.lstrip().startswith(("#","--")): continue
            n=len(raw)-len(raw.lstrip(' ')); self.lines.append(Node(raw[n:].strip(),no,n,[]))
        self.pos=0
    def parse(self): return self._block(self.lines[0].indent)[0] if self.lines else []
    def _block(self,indent):
        nodes=[]
        while self.pos<len(self.lines):
            n=self.lines[self.pos]
            if n.indent<indent: break
            if n.indent>indent: raise SyntaxError('unexpected indentation',n.line)
            self.pos+=1
            if self.pos<len(self.lines) and self.lines[self.pos].indent>indent: n.children=self._block(self.lines[self.pos].indent)[0]
            nodes.append(n)
        return nodes,self.pos

def _strip(s,word): return s[:-len(word)].rstrip() if s.rstrip().endswith(word) else s.strip()

def _expr(s):
    s=s.strip(); s=re.sub(r'\btrue\b','True',s,flags=re.I); s=re.sub(r'\bfalse\b','False',s,flags=re.I)
    for op,fn in [('!<=','__not_le__'),('!>=','__not_ge__'),('!<','__not_lt__'),('!>','__not_gt__')]:
        s=re.sub(r'(.+?)\s+'+re.escape(op)+r'\s+(.+)',lambda m:f'{fn}({m.group(1)}, {m.group(2)})',s)
    s=s.replace(' ?? ',' or ')
    for word,repl in [('nand','(not ({a} and {b}))'),('nor','(not ({a} or {b}))'),('xor','(bool({a}) != bool({b}))'),('xnor','(bool({a}) == bool({b}))')]:
        m=re.fullmatch(r'(.+?)\s+'+word+r'\s+(.+)',s)
        if m: s=repl.format(a=m.group(1),b=m.group(2))
    s=re.sub(r'\bdec\s+(-?\d+(?:\.\d+)?)',r'dec(\1)',s)
    return s

class Scope:
    def __init__(self,parent=None): self.parent=parent; self.values={}; self.const=set()
    def get(self,k):
        if k in self.values:return self.values[k]
        if self.parent:return self.parent.get(k)
        raise NameError(f"name '{k}' is not defined")
    def exists(self,k):
        try:self.get(k); return True
        except NameError:return False
    def set(self,k,v,kind=None):
        if k in self.const: raise RuntimeError(f"constant '{k}' cannot be reassigned")
        if kind=='const': self.values[k]=v; self.const.add(k); return
        if kind in ('global','all'):
            r=self
            while r.parent:r=r.parent
            r.values[k]=v; return
        self.values[k]=v

class ReturnSignal(Exception):
    def __init__(self,value):self.value=value
class BreakSignal(Exception):
    def __init__(self,count=1):self.count=count

class HookFunction:
    def __init__(self,name,params,body,closure,engine,async_=False): self.name=name;self.params=params;self.body=body;self.closure=closure;self.engine=engine;self.async_=async_
    def __str__(self): return f"function {self.name}"
    __repr__=__str__
    def __call__(self,*args,**kwargs):
        s=Scope(self.closure); pos=0
        for name,typ,default,vararg in self.params:
            if vararg: val=list(args[pos:]); pos=len(args)
            elif pos<len(args): val=args[pos];pos+=1
            elif name in kwargs: val=kwargs.pop(name)
            elif default is not None: val=self.engine.expr(default,s)
            else: raise FunctionError(f"missing argument '{name}'")
            if typ and typ not in ('Any','All') and not self.engine.check_type(val,typ): raise TypeError(f"argument '{name}' must be {typ}")
            s.values[name]=val
        if kwargs: raise FunctionError(f"unexpected arguments: {', '.join(kwargs)}")
        try:self.engine.exec_block(self.body,s)
        except ReturnSignal as r:return r.value
        return None

class HookClass:
    def __init__(self,name,bases,body,engine,scope):
        self.name=name;self.bases=bases;self.methods={};self.attrs={};self.engine=engine
        for n in body:
            if re.match(r'^(?:async\s+)?(?:function|func|def)\s+',n.text):
                f=engine.make_function(n,scope);self.methods[f.name]=f
            elif '=' in n.text:
                k,v=n.text.split('=',1);self.attrs[k.strip()]=engine.expr(v,scope)
    def __str__(self): return f"class {self.name}"
    __repr__=__str__
    def __call__(self,*args,**kwargs):
        o=HookObject(self); init=self.find('__init__') or self.find('init')
        if init:init(o,*args,**kwargs)
        return o
    def find(self,k):
        if k in self.methods:return self.methods[k]
        for b in self.bases:
            if b and hasattr(b,'find'):
                x=b.find(k)
                if x:return x

class HookObject:
    def __init__(self,cls):object.__setattr__(self,'cls',cls);object.__setattr__(self,'attrs',{})
    def __str__(self): return f"<{self.cls.name} object>"
    __repr__=__str__
    def __getattr__(self,k):
        if k in self.attrs:return self.attrs[k]
        c=self.cls
        while c:
            if k in c.attrs:return c.attrs[k]
            f=c.find(k)
            if f:return lambda *a,**kw:f(self,*a,**kw)
            c=c.bases[0] if c.bases else None
        raise AttributeError(f"object has no attribute '{k}'")
    def __setattr__(self,k,v):self.attrs[k]=v

class Engine:
    def __init__(self,filename=None): self.filename=filename;self.root=Scope();self._builtins()
    def _builtins(self):
        def rng(a,b=None,step=1): return list(range(a,b,step)) if b is not None else list(range(1,a+1,step))
        type_names=['text','num','decimal','boolean','None','Any','All','list','unique','data','group','Object','Type','Concept','Operator','Loop']
        types={name:HookType(name) for name in type_names}
        error_types={name:HookErrorType(name,cls) for name,cls in ERRORS.items()}
        def make_text(x): return str(x)
        def make_num(x): return int(x)
        def make_decimal(x): return float(x)
        def make_boolean(x): return bool(x)
        types['text'].converter=make_text; types['num'].converter=make_num; types['decimal'].converter=make_decimal; types['boolean'].converter=make_boolean
        self.root.values.update({
          'True':True,'False':False,'None':None,'print':hook_print,'input':input,'len':len,'range':rng,
          'abs':abs,'min':min,'max':max,'sum':sum,'round':round,'bool':bool,'str':str,'int':int,'float':float,
          'text':types['text'],'num':types['num'],'decimal':types['decimal'],'dec':types['decimal'],'boolean':types['boolean'],
          'list':types['list'],'unique':types['unique'],'data':types['data'],'group':types['group'],
          'Object':types['Object'],'Type':types['Type'],'Concept':types['Concept'],'Operator':types['Operator'],'Loop':types['Loop'],
          'type':self.type_name,'convert':self.convert,
          '__not_le__':lambda a,b:not a<=b,'__not_ge__':lambda a,b:not a>=b,'__not_lt__':lambda a,b:not a<b,'__not_gt__':lambda a,b:not a>b
        })
        self.root.values.update(error_types)
    def type_name(self,x):
        if isinstance(x,HookType):return 'Type'
        if isinstance(x,HookErrorType):return 'Type'
        if isinstance(x,HookClass):return x.name
        if isinstance(x,HookFunction):return 'function'
        if isinstance(x,HookObject):return x.cls.name
        if isinstance(x,HookError):return x.__class__.__name__
        if x is None:return 'None'
        if isinstance(x,bool):return 'boolean'
        if isinstance(x,int) and not isinstance(x,bool):return 'num'
        if isinstance(x,float):return 'decimal'
        if isinstance(x,str):return 'text'
        if isinstance(x,list):return 'list'
        if isinstance(x,tuple):return 'unique'
        if isinstance(x,dict):return 'data'
        return x.__class__.__name__
    def convert(self,x,t):
        n=t.name if isinstance(t,HookType) else (t if isinstance(t,str) else getattr(t,'__name__',str(t)))
        f={'text':str,'num':int,'decimal':float,'dec':float,'boolean':bool}.get(n)
        if not f: raise TypeError(f"cannot convert to {n}")
        try:return f(x)
        except Exception as e:raise ValueError(str(e))
    def check_type(self,v,t): return t in ('Any','All',self.type_name(v)) or (t=='decimal' and isinstance(v,(int,float)))
    def expr(self,s,scope):
        try:
            env={}; chain=[];p=scope
            while p:chain.append(p);p=p.parent
            for q in reversed(chain):env.update(q.values)
            return eval(_expr(s),{'__builtins__':{}},env)
        except HookError:raise
        except NameError as e:raise NameError(str(e))
        except Exception as e:raise ExecutionError(str(e))
    def make_function(self,node,scope):
        m=re.match(r'(?:async\s+)?(?:function|func|def)\s+([A-Za-z_]\w*)\s*\((.*?)\)',node.text)
        if not m:raise SyntaxError('invalid function declaration',node.line)
        ps=[]
        for raw in [x.strip() for x in m.group(2).split(',') if x.strip()]:
            var=raw.startswith('*'); raw=raw[1:].strip() if var else raw; default=None
            if '=' in raw:raw,default=raw.split('=',1);raw=raw.strip();default=default.strip()
            typ=None
            if ':' in raw:raw,typ=raw.split(':',1);raw=raw.strip();typ=typ.strip()
            ps.append((raw,typ,default,var))
        return HookFunction(m.group(1),ps,node.children or [],scope,self,node.text.startswith('async'))
    def assign(self,lhs,val,scope,kind=None):
        lhs=lhs.strip()
        if re.fullmatch(r'[A-Za-z_]\w*',lhs):
            if kind=='reassign' and not scope.exists(lhs):raise NameError(f"cannot reassign undefined variable '{lhs}'")
            scope.set(lhs,val,'local' if kind in ('local','reassign') else kind);return
        m=re.fullmatch(r'(.+)\.([A-Za-z_]\w*)',lhs)
        if m:setattr(self.expr(m.group(1),scope),m.group(2),val);return
        raise SyntaxError('invalid assignment target')
    def _clauses(self,nodes,i,prefixes):
        j=i+1; found={}
        while j<len(nodes) and any(nodes[j].text==p or nodes[j].text.startswith(p+' ') for p in prefixes):
            k=nodes[j].text.split()[0];found[k]=nodes[j];j+=1
        return found,j
    def _run_loop_body(self,n,scope):
        try:self.exec_block(n.children or [],Scope(scope))
        except BreakSignal as b:return b
        return None
    def exec_block(self,nodes,scope):
        i=0
        while i<len(nodes):
            n=nodes[i];s=n.text
            if s in ('else','finally') or s.startswith(('elif ','except ','catch ')):i+=1;continue
            m=re.match(r'^(local|global|all|const|reassign)\s+(.+?)\s*=\s*(.*)$',s)
            if m:self.assign(m.group(2),self.expr(m.group(3),scope),scope,m.group(1));i+=1;continue
            if re.match(r'^(?:async\s+)?(?:function|func|def)\s+',s):
                f=self.make_function(n,scope);scope.values[f.name]=f;i+=1;continue
            if s.startswith('class '):
                m=re.match(r'class\s+([A-Za-z_]\w*)\s*\((.*?)\):?$',s)
                if not m:raise SyntaxError('invalid class declaration',n.line)
                bs=[]
                for b in [x.strip() for x in m.group(2).split(',') if x.strip()]:
                    try:bs.append(scope.get(b))
                    except NameError:bs.append(None)
                scope.values[m.group(1)]=HookClass(m.group(1),bs,n.children or [],self,scope);i+=1;continue
            if s.startswith('if '):
                chain=[n];j=i+1
                while j<len(nodes) and (nodes[j].text.startswith('elif ') or nodes[j].text=='else'):chain.append(nodes[j]);j+=1
                for c in chain:
                    if c.text=='else' or self.expr(_strip(c.text[2:].strip(),'then'),scope):self.exec_block(c.children or [],Scope(scope));break
                i=j;continue
            if s=='try':
                clauses,j=self._clauses(nodes,i,['except','catch','finally']);err=None
                try:self.exec_block(n.children or [],Scope(scope))
                except Exception as e:err=e
                if err:
                    handled=False
                    for key,c in clauses.items():
                        if key=='finally':continue
                        head=c.text.split(None,1)[1] if ' ' in c.text else ''
                        typ=head.strip()
                        if not typ or typ=='*' or typ==err.__class__.__name__:
                            self.exec_block(c.children or [],Scope(scope));handled=True;break
                    if not handled:raise err
                if 'finally' in clauses:self.exec_block(clauses['finally'].children or [],Scope(scope))
                i=j;continue
            if s.startswith(('while ','for ','foreach ','repeat','forever','until ')):
                clauses,j=self._clauses(nodes,i,['else','finally']);broke=False;error=None
                try:
                    if s.startswith('while '):
                        cond=_strip(s[6:].strip(),'do')
                        while self.expr(cond,scope):
                            b=self._run_loop_body(n,scope)
                            if b:
                                if b.count>1:b.count-=1;raise b
                                broke=True;break
                    elif s.startswith('for ' ) or s.startswith('foreach '):
                        m=re.match(r'(?:for|foreach)\s+([A-Za-z_]\w*)\s+in\s+(.+?)\s+do$',s)
                        if not m:raise SyntaxError('invalid for/foreach loop',n.line)
                        for v in self.expr(m.group(2),scope):
                            scope.values[m.group(1)]=v;b=self._run_loop_body(n,scope)
                            if b:
                                if b.count>1:b.count-=1;raise b
                                broke=True;break
                    elif s.startswith('repeat'):
                        m=re.match(r'repeat(?:\s+(\d+))?\s*do$',s)
                        if not m:raise SyntaxError('invalid repeat loop',n.line)
                        count=int(m.group(1)) if m.group(1) else None;k=0
                        while count is None or k<count:
                            b=self._run_loop_body(n,scope)
                            if b:
                                if b.count>1:b.count-=1;raise b
                                broke=True;break
                            k+=1
                    elif s.startswith('forever'):
                        while True:
                            b=self._run_loop_body(n,scope)
                            if b:
                                if b.count>1:b.count-=1;raise b
                                broke=True;break
                    else:
                        cond=_strip(s[6:].strip(),'do')
                        while not self.expr(cond,scope):
                            b=self._run_loop_body(n,scope)
                            if b:
                                if b.count>1:b.count-=1;raise b
                                broke=True;break
                except Exception as e:error=e
                finally:
                    if 'finally' in clauses:
                        self.exec_block(clauses['finally'].children or [],Scope(scope))
                if error is not None:raise error
                if 'else' in clauses and not broke:self.exec_block(clauses['else'].children or [],Scope(scope))
                i=j;continue
            if s.startswith('return'):
                r=s[6:].strip();raise ReturnSignal(tuple(self.expr(x.strip(),scope) for x in r.split(',')) if ',' in r else (self.expr(r,scope) if r else None))
            if s.startswith('break'):
                p=s.split();raise BreakSignal(int(p[1]) if len(p)>1 else 1)
            if s.startswith('raise '):
                e=self.expr(s[6:].strip(),scope);raise e if isinstance(e,Exception) else RuntimeError(str(e))
            if s.startswith('do '):self.expr(s[3:],scope);i+=1;continue
            if '=' in s and not any(x in s for x in ('==','!=','<=','>=')):
                l,r=s.split('=',1);self.assign(l,self.expr(r,scope),scope);i+=1;continue
            self.expr(s,scope);i+=1
    def run(self,source):self.exec_block(Parser(source).parse(),self.root);return self.root

def compile_source(source,filename=None):return Parser(source).parse()
def execute(source,filename=None,scope=None):
    e=Engine(filename)
    if scope is not None:e.root=scope
    e.run(source);return e.root

def run(source_or_path):
    p=Path(source_or_path)
    if p.exists() and p.suffix=='.hk':return Engine(str(p)).run(p.read_text(encoding='utf-8'))
    return Engine().run(str(source_or_path))
