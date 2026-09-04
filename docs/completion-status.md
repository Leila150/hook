# HOOK 1.x Completion Status

This document tracks executable work. A feature is marked implemented only when concrete code and regression coverage exist; external toolchains are detected and used rather than simulated.

## Implemented

- Token-aware dialect transformations that preserve strings/comments.
- Expression VM for arithmetic, comparisons, boolean logic, collections, indexing and registered calls.
- Reverse-mode scalar automatic differentiation.
- Neural-network primitives: linear, ReLU, softmax, model state, SGD and Adam.
- Async task scheduler, gathering, cancellation and async channels.
- Source diagnostics, source maps, profiler and debugger primitives.
- `.hk` module and package-init resolution.
- Native target discovery and canonical triples.
- Real C compilation through an installed clang/gcc/cc compiler plus ctypes FFI.
- Real Gradle Android project generation and conditional APK building when Gradle is installed.
- Versioned atomic serialization.
- SQLite database API and threaded TCP server.
- Tkinter GUI primitives and a deterministic 2D game/entity loop with AABB collision.
- Formatter and linter primitives.
- Minimal stdio JSON-RPC LSP server.
- Project manifest and local package installation helpers.
- Unified completion/full-runtime public exports.
- Regression tests covering the newly implemented services.

## External backend boundary

HOOK can now invoke real native/platform toolchains where installed. It still does not bundle LLVM, Android SDK/build-tools, GPU drivers, Vulkan/OpenGL implementations, a C++ compiler, Rustc, or a production 3D/LLM backend. Those are platform toolchains rather than Python source files; the runtime reports missing prerequisites instead of silently pretending they exist.
