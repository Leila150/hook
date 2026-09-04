"""HOOK 1.0 command-line interface."""
from __future__ import annotations
import argparse,pathlib,os
from .cli_ui import banner,error,info
from .engine import Engine
from .runtime_extensions import install_engine_extensions
from .errors import HookError
from .compat import WinlatorRuntime,CompatibilityError,detect_components,host_arch,is_android
install_engine_extensions(Engine);VERSION='1.0.0'
def _run_file(path):
 if not path.exists():error(f'file not found: {path}');return 1
 if not path.is_file():error(f'not a file: {path}');return 1
 if path.suffix!='.hk':error('HOOK source files must use .hk');return 1
 try:Engine(str(path)).run(path.read_text(encoding='utf-8'));return 0
 except HookError as exc:error(str(exc));return 1
 except Exception as exc:error(f'SystemError: {exc}');return 1
def _compat_status():
 print(f'host: {host_arch()} | android: {"yes" if is_android() else "no"}')
 for n,c in detect_components().items():print(f'{n}: {"available" if c.available else "missing"}'+(f' — {c.version}' if c.version else ''))
 return 0
def _compat_run(executable,args):
 try:return WinlatorRuntime().run(executable,args)
 except CompatibilityError as exc:error(str(exc));info('Set HOOK_ROOTFS, HOOK_WINEPREFIX and component paths for a custom compatibility environment.');return 1
 except Exception as exc:error(f'CompatibilityError: {exc}');return 1
def repl():
 banner();info('HOOK 1.0 interactive mode. Type :help for commands, :quit to exit.');e=Engine()
 while True:
  try:s=input('hook> ')
  except (EOFError,KeyboardInterrupt):print();return 0
  c=s.strip().lower()
  if c in {':quit',':q',':exit'}:return 0
  if c in {':help',':h'}:print(':help  show help\n:quit  exit HOOK\n:version  show version\n:features  list runtime features\n:clear  clear terminal');continue
  if c==':version':print(f'HOOK {VERSION}');continue
  if c==':features':print('\n'.join(e.features.names()));continue
  if c==':clear':print('\033[2J\033[H',end='');continue
  if not s.strip():continue
  try:e.run(s)
  except HookError as exc:error(str(exc))
  except Exception as exc:error(f'SystemError: {exc}')
def build_parser():
 p=argparse.ArgumentParser(prog='hook',description='HOOK 1.0 — easy, powerful, extensible, universal.')
 p.add_argument('target',nargs='?',help='repl, run, compat, or a .hk source file');p.add_argument('file',nargs='?',help='.hk file or compat action');p.add_argument('compat_args',nargs=argparse.REMAINDER,help='compatibility action arguments');p.add_argument('-c','--code',metavar='CODE');p.add_argument('--version',action='version',version=f'HOOK {VERSION}');return p
def main(argv=None):
 ns=build_parser().parse_args(argv)
 if ns.target=='repl':return repl()
 if ns.code is not None:
  try:Engine().run(ns.code);return 0
  except HookError as exc:error(str(exc));return 1
  except Exception as exc:error(f'SystemError: {exc}');return 1
 if ns.target=='compat':
  rt=WinlatorRuntime();action=ns.file or 'status';args=ns.compat_args
  if action=='status':return _compat_status()
  if action=='doctor':
   print(rt.doctor());return 0
  if action=='list':
   print('\n'.join(rt.list_profiles()) or 'No compatibility profiles.');return 0
  if action=='create':
   if not args:error('compat create requires a profile name');return 2
   print(rt.create_profile(args[0]));return 0
  if action=='inspect':
   if not args:error('compat inspect requires a profile name');return 2
   try:print(rt.load_profile(args[0]).to_json())
   except Exception as exc:error(str(exc));return 1
   return 0
  if action=='run':
   if not args:error('compat run requires an executable path');return 2
   return _compat_run(args[0],args[1:])
  error(f'unknown compat action: {action}');return 2
 if ns.target=='run':return _run_file(pathlib.Path(ns.file)) if ns.file else 2
 if ns.target is None:build_parser().print_help();return 0
 return _run_file(pathlib.Path(ns.target))
if __name__=='__main__':raise SystemExit(main())
