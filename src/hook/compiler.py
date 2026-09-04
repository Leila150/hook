"""Small HOOK bytecode layer.
The v0.1 interpreter remains authoritative; bytecode is a stable intermediate representation that can later gain native code generation without changing source semantics.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class Instruction:
    op:str
    arg:object=None
@dataclass
class Program:
    instructions:list
    source:str=""

class Compiler:
    def compile(self,source):
        # One instruction per source line keeps compilation deterministic and
        # preserves indentation exactly for the interpreter-backed VM.
        return Program([Instruction("SOURCE",line) for line in source.splitlines()],source)

class VM:
    def __init__(self,engine): self.engine=engine
    def run(self,program): return self.engine.run(program.source)

def compile_source(source): return Compiler().compile(source)
