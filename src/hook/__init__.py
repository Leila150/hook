"""HOOK v0.1 public API."""
from .engine import run, execute, compile_source, Lexer, Parser, Engine
from .errors import HookError
from .runtime_extensions import install_engine_extensions
from .extension_system import (ExtensionBase, Type, Error, Statement, Loop, Operator, Language, Processor, ExtensionDefinition, ExtensionRegistry, ExtensionConflict, CATEGORIES, install_extension_system)
from .universal_runtime import install_universal_runtime
from .extension_runtime import install_extension_runtime
from .compiler import Compiler, VM, Program, Instruction
from .language_core import ASTNode, ASTParser, SemanticAnalyzer, SemanticError, BytecodeCompiler, BytecodeProgram, LanguagePipeline
from .persistence import HKD, HKDError, PersistentScope, PersistentScopes
from .tooling import Formatter, Linter, Diagnostic, Profiler, TestRunner
from .package_manager import Package, PackageManager
from .interop import NativeLibrary, CInterop, CppInterop, RustInterop, ABI
from .ai_core import Tensor, tensor, softmax, argmax, relu, sigmoid, linear, Sequential, ModelRegistry
from .diagnostics_core import SourcePosition, TraceFrame, TracebackBuilder, SourceMap, DiagnosticEngine

install_engine_extensions(Engine)
install_extension_system(Engine)
install_universal_runtime(Engine)
install_extension_runtime(Engine)

__version__="0.1.0"
__all__=["run","execute","compile_source","Lexer","Parser","Engine","Compiler","VM","Program","Instruction","HookError","__version__","ExtensionBase","Type","Error","Statement","Loop","Operator","Language","Processor","ExtensionDefinition","ExtensionRegistry","ExtensionConflict","CATEGORIES","ASTNode","ASTParser","SemanticAnalyzer","SemanticError","BytecodeCompiler","BytecodeProgram","LanguagePipeline","HKD","HKDError","PersistentScope","PersistentScopes","Formatter","Linter","Diagnostic","Profiler","TestRunner","Package","PackageManager","NativeLibrary","CInterop","CppInterop","RustInterop","ABI","Tensor","tensor","softmax","argmax","relu","sigmoid","linear","Sequential","ModelRegistry","SourcePosition","TraceFrame","TracebackBuilder","SourceMap","DiagnosticEngine"]
