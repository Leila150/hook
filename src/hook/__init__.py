"""HOOK v0.1 public API."""
from .engine import run, execute, compile_source, Lexer, Parser, Engine
from .errors import HookError
from .runtime_extensions import install_engine_extensions
from .compiler import Compiler, VM, Program, Instruction
install_engine_extensions(Engine)
__version__="0.1.0"
__all__=["run","execute","compile_source","Lexer","Parser","Engine","Compiler","VM","Program","Instruction","HookError","__version__"]
