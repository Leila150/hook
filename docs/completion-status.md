# HOOK 1.x Completion Status

This document tracks implemented runtime work. A feature is marked implemented only when there is executable code or a regression test; metadata-only placeholders are not counted.

## Completed in this pass

- Token-aware dialect keyword, statement and operator transformation that preserves strings and comments.
- Dependency-free expression VM for arithmetic, comparisons, boolean logic, collections, indexing and registered calls.
- Reverse-mode scalar automatic differentiation with `Value.backward()`.
- Async task scheduler with spawn, gather and cancellation.
- Async channel primitive.
- Source diagnostics with positions, severities and error codes.
- Module resolution for `.hk` modules, package `__init__.hk`, and built-in runtime modules.
- Native target discovery and canonical target triples for Linux, Windows, macOS and Android ARM targets.
- Versioned atomic serializer for persistent data values.
- Unified `CompletePipeline` facade and public exports.
- VM jump regression coverage and completion subsystem regression coverage.

## Backend boundary

Android APK generation, GPU execution, C/C++/Rust compilation, a full 3D renderer and a full LLM backend require substantial native/platform backends. HOOK exposes stable interfaces for these systems, but does not pretend a metadata class is a working compiler or renderer. Native builds should activate when the required host toolchain exists.
