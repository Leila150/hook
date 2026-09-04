"""HOOK v0.1 error hierarchy."""

class HookError(Exception):
    """Base exception for HOOK programs."""
    def __init__(self, message, line=None, column=None, source=None):
        self.message, self.line, self.column, self.source = message, line, column, source
        super().__init__(self.format())
    def format(self):
        where = ""
        if self.line is not None:
            where = f" at line {self.line}"
            if self.column is not None: where += f", column {self.column}"
        return f"{self.__class__.__name__}{where}: {self.message}"

class SyntaxError(HookError): pass
class NameError(HookError): pass
class TypeError(HookError): pass
class ValueError(HookError): pass
class AttributeError(HookError): pass
class IndexError(HookError): pass
class KeyError(HookError): pass
class ImportError(HookError): pass
class FileError(HookError): pass
class RuntimeError(HookError): pass
class MemoryError(HookError): pass
class ArithmeticError(HookError): pass
class DivisionError(ArithmeticError): pass
class OverflowError(ArithmeticError): pass
class NumericError(ArithmeticError): pass
class LoopError(HookError): pass
class FunctionError(HookError): pass
class ClassError(HookError): pass
class OperatorError(HookError): pass
class PackageError(HookError): pass
class CompileError(HookError): pass
class ExecutionError(HookError): pass
class SystemError(HookError): pass

ERRORS = {c.__name__: c for c in [HookError, SyntaxError, NameError, TypeError, ValueError,
 AttributeError, IndexError, KeyError, ImportError, FileError, RuntimeError, MemoryError,
 ArithmeticError, DivisionError, OverflowError, NumericError, LoopError, FunctionError,
 ClassError, OperatorError, PackageError, CompileError, ExecutionError, SystemError]}
