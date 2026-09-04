"""HOOK 1.x public API."""
from .engine import run, execute, compile_source, Lexer, Parser, Engine
from .errors import HookError
from .runtime_extensions import install_engine_extensions
from .extension_system import ExtensionBase, Type, Error, Statement, Loop, Operator, Language, Processor, ExtensionDefinition, ExtensionRegistry, ExtensionConflict, CATEGORIES, install_extension_system
from .universal_runtime import install_universal_runtime
from .extension_runtime import install_extension_runtime
from .compiler import Compiler, VM, Program, Instruction
from .language_core import ASTNode, ASTParser, SemanticAnalyzer, SemanticError, BytecodeCompiler, BytecodeProgram, LanguagePipeline
from .persistence import HKD, HKDError, PersistentScope, PersistentScopes
from .tooling import Formatter, Linter, Diagnostic, Profiler, TestRunner
from .package_manager import Package, PackageManager, Version, satisfies
from .interop import NativeLibrary, CInterop, CppInterop, RustInterop, ABI
from .ai_core import Tensor as CoreTensor, tensor, softmax, argmax, relu, sigmoid, linear, Sequential, ModelRegistry
from .ai_training import Parameter, Optimizer, SGD, Adam, mse, binary_cross_entropy, Dataset
from .ai_advanced import Tensor, Module, Linear, LayerNorm, MultiHeadAttention, FeedForward, TransformerBlock, TinyTransformer, CharTokenizer
from .diagnostics_core import SourcePosition, TraceFrame, TracebackBuilder, SourceMap, DiagnosticEngine
from .concurrency import CancellationToken, Channel, TaskGroup, Scheduler, Mutex, Atom
from .memory import Pointer, MemoryManager, Unsafe
from .native_bindings import Ownership, Binding, NativeBindings
from .vm_core import Op, Bytecode, VM as CoreVM
from .web_framework import Request, Response, Router, WebApp
from .game_runtime import Color, Vec2, Entity, Scene, Game, GUI, Audio
from .toolchain import TARGETS, TRIPLES, Tool, find_tool, Project, AndroidToolchain, Codegen
from .dialects import Dialect, DialectEngine, SyntaxExtension, ExtensionPipeline
from .graphics_runtime import Vec3, Camera, Mesh, SoftwareRenderer, GPUBackend
from .engine3d import Vec3 as Vec3D, Vec2 as Vec2D, Color as Color3D, Texture2D, Transform, Material, Mesh3D, Camera3D, Light, DirectionalLight, Ray3D, AABB, mesh_bounds, Object3D, Keyframe, AnimationTrack, Animation, Scene3D, Software3DRenderer, GraphicsBackend, OpenGLBackend, VulkanBackend, GPU3DBackend, Engine3D
from .engine3d_assets import Hit3D, ray_aabb, ray_triangle, ray_mesh, load_gltf, AssetLoader, CollisionWorld
from .physics3d import RigidBody3D, PhysicsWorld3D, SphereCollider
from .scene_io import save_scene, load_scene
from .shaders3d import ShaderContext, Shader, ShaderLibrary
from .game_io import InputState, InputManager, Sound, AudioManager, Clock
from .compat import Component, CompatibilityConfig, CompatibilityError, detect_components, is_android, host_arch, ArchitectureTranslator, WineRuntime, ContainerProfile, WinlatorRuntime
from .build_system import BuildTarget, NativeBuilder, find_android_sdk, find_android_ndk, AndroidProject
from .full_runtime import (TensorValue, ParameterValue, LinearLayer, ReLULayer, SoftmaxLayer, NeuralModel, SGDOptimizer, AdamOptimizer, mse_loss, cross_entropy, NativeToolchain, find_native_compiler, compile_c, load_library, CFFI, AndroidProject as FullAndroidProject, GUIRuntime, GameEntity, GameRuntime, Database, TCPServer, format_hook, lint_hook, Debugger, LSPServer)
from .completion import Position, Diagnostics, SourceAnalyzer, ExpressionVM, Value, TaskScheduler, AsyncChannel, ModuleSpec, ModuleResolver, NativeTarget, TargetResolver, Serializer, CompilationResult, CompletePipeline
from .v1_runtime import VERSION, LANGUAGE, Module, FeatureRegistry, install_v1_runtime
from .v1_fixes import install_v1_fixes
install_engine_extensions(Engine); install_extension_system(Engine); install_universal_runtime(Engine); install_extension_runtime(Engine); install_v1_runtime(Engine); install_v1_fixes(Engine)
__version__=VERSION
__all__=[name for name in globals() if not name.startswith('_')]
