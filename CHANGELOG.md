# Changelog

## 1.1.1 — 2026-09-04

Correctness and portability release following the deep runtime audit.

### Fixed
- Removed unsafe loop-execution monkeypatching from the compatibility layer.
- Preserved existing-variable assignment semantics and constant enforcement.
- Fixed extension handlers receiving the wrong scope.
- Fixed custom operators to dispatch evaluated values without `repr()` source reconstruction.
- Fixed middleware fallback so real `TypeError` exceptions are not silently retried with another signature.
- Added synchronous and asynchronous web dispatch paths and graceful server shutdown.
- Added typed web route parameter conversion for numeric and boolean parameters.
- Fixed JSON response bodies being stored as text instead of bytes.
- Fixed package dependency resolution to intersect constraints with deterministic backtracking.
- Fixed Python 3.10 TOML support through the `tomli` compatibility dependency.
- Fixed asynchronous HOOK functions so their body is deferred until awaited.
- Added deterministic multiple-inheritance method resolution.
- Fixed transformer linear layers for batched `[sequence, features]` tensors.
- Fixed multi-head attention to compute every configured attention head.
- Added tensor broadcasting for compatible singleton dimensions.
- Added `CompilationResult.ok()` for the completion pipeline API.
- Corrected the test import for `Serializer` and expanded regression coverage.
- Hardened mobile project generation and explicitly report when a native HOOK runtime is not embedded.

### Release baseline
- Package version: `1.1.1`
- Source extension: `.hk`
- No `end` keyword.
- No `continue` keyword.

## 1.0.0 — 2026-09-04

HOOK 1.0 consolidates the interpreter and runtime foundations into a single public release line.

### Added
- Integrated runtime feature registry and built-in modules.
- Native `api METHOD "/path" do` routing syntax.
- `serve` command inside HOOK source.
- Built-in JSON, OS, math, random, path, time and async modules.
- Unified AI, game, concurrency, memory, native, tooling, package and dialect modules.
- Constant enforcement and safer nested async awaiting.
- Expanded web responses, middleware, routing helpers and HTTP methods.
- HOOK 1.0 specification, examples and CI/build automation.

### Release baseline
- Package version: `1.0.0`
- Source extension: `.hk`
- No `end` keyword.
- No `continue` keyword.
