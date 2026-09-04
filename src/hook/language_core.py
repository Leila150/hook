"""Production-oriented language core helpers for HOOK.

This module provides the pieces that sit between the existing v0.1 engine and a
future native compiler: tokens, AST nodes, semantic analysis, extension-aware
syntax, and a deterministic bytecode IR.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Iterable
import re

@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    line: int
    column: int

@dataclass
class ASTNode:
    kind: str
    value: Any = None
    children: list["ASTNode"] = field(default_factory=list)
    line: int = 0
    column: int = 0

class ASTParser:
    """Indentation-aware parser producing a stable AST for tooling/compiler use."""
    def __init__(self, source: str):
        self.source = source
        self.lines = []
        for line_no, raw in enumerate(source.splitlines(), 1):
            if not raw.strip() or raw.lstrip().startswith(("#", "--")):
                continue
            indent = len(raw) - len(raw.lstrip(" "))
            self.lines.append((line_no, indent, raw.strip()))
        self.pos = 0

    def parse(self) -> ASTNode:
        root = ASTNode("module")
        root.children = self._block(self.lines[0][1] if self.lines else 0)
        return root

    def _block(self, indent: int) -> list[ASTNode]:
        out = []
        while self.pos < len(self.lines):
            line, level, text = self.lines[self.pos]
            if level < indent:
                break
            if level > indent:
                raise SyntaxError(f"unexpected indentation at line {line}")
            self.pos += 1
            node = self._node(text, line)
            if self.pos < len(self.lines) and self.lines[self.pos][1] > indent:
                node.children = self._block(self.lines[self.pos][1])
            out.append(node)
        return out

    def _node(self, text: str, line: int) -> ASTNode:
        patterns = [
            (r"^(?:local|global|all|const|reassign)\\b", "declaration"),
            (r"^(?:if|elif|else)\\b", "condition"),
            (r"^(?:while|for|foreach|repeat|until|forever)\\b", "loop"),
            (r"^(?:async\\s+)?(?:function|func|def)\\b", "function"),
            (r"^class\\b", "class"),
            (r"^(?:try|except|catch|finally)\\b", "exception"),
            (r"^import\\b|^from\\b", "import"),
            (r"^return\\b", "return"),
            (r"^break(?:\\s+\\d+)?$", "break"),
            (r"^raise\\b", "raise"),
        ]
        for pattern, kind in patterns:
            if re.search(pattern, text):
                return ASTNode(kind, text, line=line, column=1)
        return ASTNode("statement", text, line=line, column=1)

class SemanticError(Exception): pass

class SemanticAnalyzer:
    def __init__(self):
        self.scopes: list[set[str]] = [set()]
        self.errors: list[str] = []

    def analyze(self, tree: ASTNode) -> list[str]:
        self._walk(tree)
        return self.errors

    def _walk(self, node: ASTNode):
        if node.kind == "declaration":
            m = re.match(r"(?:local|global|all|const|reassign)\\s+([A-Za-z_]\\w*)", str(node.value))
            if m and str(node.value).startswith("reassign") and not any(m.group(1) in s for s in self.scopes):
                self.errors.append(f"line {node.line}: cannot reassign undefined variable '{m.group(1)}'")
            elif m and not str(node.value).startswith("reassign"):
                self.scopes[-1].add(m.group(1))
        if node.kind in {"function", "class", "loop", "condition", "exception"}:
            self.scopes.append(set())
            for child in node.children: self._walk(child)
            self.scopes.pop()
            return
        for child in node.children: self._walk(child)

@dataclass(frozen=True)
class Instruction:
    opcode: str
    operands: tuple[Any, ...] = ()
    line: int = 0

@dataclass
class BytecodeProgram:
    instructions: list[Instruction] = field(default_factory=list)
    constants: list[Any] = field(default_factory=list)

class BytecodeCompiler:
    """Deterministic IR compiler. Runtime-specific lowering is deliberately separate."""
    def compile(self, tree: ASTNode) -> BytecodeProgram:
        p = BytecodeProgram()
        self._compile_nodes(tree.children, p)
        p.instructions.append(Instruction("HALT"))
        return p

    def _compile_nodes(self, nodes: Iterable[ASTNode], p: BytecodeProgram):
        for n in nodes:
            if n.kind == "return":
                p.instructions.append(Instruction("RETURN", (str(n.value)[6:].strip(),), n.line))
            elif n.kind == "break":
                parts = str(n.value).split(); p.instructions.append(Instruction("BREAK", (int(parts[1]) if len(parts)>1 else 1,), n.line))
            elif n.kind == "function":
                p.instructions.append(Instruction("DEFINE_FUNCTION", (str(n.value),), n.line))
            elif n.kind == "class":
                p.instructions.append(Instruction("DEFINE_CLASS", (str(n.value),), n.line))
            else:
                p.instructions.append(Instruction("EXEC_SOURCE", (str(n.value),), n.line))
            if n.children:
                self._compile_nodes(n.children, p)

class LanguagePipeline:
    def compile(self, source: str) -> BytecodeProgram:
        tree = ASTParser(source).parse()
        errors = SemanticAnalyzer().analyze(tree)
        if errors: raise SemanticError("; ".join(errors))
        return BytecodeCompiler().compile(tree)
