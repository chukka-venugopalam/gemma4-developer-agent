#!/usr/bin/env python3
"""Static checks for a declarative submission directory or ZIP. Not the official compiler."""
from __future__ import annotations
import argparse, re, sys, zipfile
from pathlib import Path, PurePosixPath
try:
    import yaml
except ImportError:
    print('BLOCKED: PyYAML missing. Install the local dev dependency: pip install -r requirements-dev.txt')
    raise SystemExit(3)
ALLOWED_EXT={'.yaml','.yml','.md','.txt','.py','.json','.safetensors'}
TOOLS={'run_command','read_file','edit_file','write_file','get_status','submit_patch','get_code_neighbors','search_similar_code','get_code_subgraph'}
MODEL='gemma-4-31b-it-qat-w4a16-ct'
class IncludeRef(str): pass
class Loader(yaml.SafeLoader): pass
Loader.add_constructor('!include', lambda loader,node: IncludeRef(loader.construct_scalar(node)))
def parse_yaml(p:Path):
    return yaml.load(p.read_text(encoding='utf-8'),Loader=Loader)
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('target',type=Path,nargs='?',default=Path('submission'))
    args=ap.parse_args(); target=args.target.resolve(); checks=[]; errors=[]
    def check(name,ok,detail=''):
        checks.append((name,bool(ok),detail))
        if not ok: errors.append(name)
    extracted=None
    if target.is_file() and target.suffix.lower()=='.zip':
        try:
            with zipfile.ZipFile(target) as z:
                bad=z.testzip(); check('ZIP CRC integrity',bad is None,str(bad or 'clean'))
                names=z.namelist(); unsafe=[]
                for n in names:
                    pos=PurePosixPath(n)
                    if pos.is_absolute() or '..' in pos.parts or '\\' in n or '\x00' in n: unsafe.append(n)
                check('Safe archive paths',not unsafe,', '.join(unsafe[:5]))
                files=[n for n in names if not n.endswith('/')]
                roots=[n for n in files if '/' not in n and Path(n).name in ('agent.yaml','agent.yml','root_agent.yaml','root_agent.yml')]
                check('Exactly one root agent config',len(roots)==1,str(roots))
                unsupported=[n for n in files if Path(n).suffix.lower() not in ALLOWED_EXT]
                check('Allowed file extensions',not unsupported,', '.join(unsupported[:10]))
                # Parse from an in-memory temporary workspace so includes can resolve.
                import tempfile
                with tempfile.TemporaryDirectory() as td:
                    z.extractall(td); root=Path(td)
                    validate_dir(root,check)
        except Exception as e:
            check('ZIP readable',False,repr(e))
    elif target.is_dir(): validate_dir(target,check)
    else:
        print(f'FAIL: target not found: {target}'); return 2
    for name,ok,detail in checks:
        print(('PASS' if ok else 'FAIL')+' | '+name+((' | '+detail) if detail else ''))
    print(f'\nSTATIC RESULT: {len(checks)-len(errors)}/{len(checks)} passed')
    print('NOTICE: these are local static checks only; they do not replace the official competition compiler or a Gemma run.')
    return 1 if errors else 0
def validate_dir(root:Path,check):
    agents=[p for p in root.iterdir() if p.is_file() and p.name in ('agent.yaml','agent.yml','root_agent.yaml','root_agent.yml')]
    check('Root agent config present exactly once',len(agents)==1,str([p.name for p in agents]))
    if len(agents)!=1:return
    try: cfg=parse_yaml(agents[0])
    except Exception as e:
        check('Root YAML parses',False,repr(e)); return
    check('Root YAML parses',isinstance(cfg,dict),'')
    if not isinstance(cfg,dict):return
    check('Model matches required base model',cfg.get('model')==MODEL,str(cfg.get('model')))
    tools=cfg.get('tools',[])
    bad=[t for t in tools if not isinstance(t,str) or t not in TOOLS]
    check('Declared tools belong to documented base registry',not bad,str(bad))
    inc_errors=[]; brace_errors=[]
    for yp in root.rglob('*'):
        if not yp.is_file() or yp.suffix.lower() not in ('.yaml','.yml'): continue
        try: data=parse_yaml(yp)
        except Exception as e:
            inc_errors.append(f'{yp.relative_to(root)}: YAML {e}'); continue
        for parent,inc in walk_includes(data):
            raw=str(inc)
            pp=PurePosixPath(raw)
            if pp.is_absolute() or '..' in pp.parts or '\x00' in raw:
                inc_errors.append(f'{yp.relative_to(root)}: unsafe include {raw}'); continue
            dest=(yp.parent/Path(raw)).resolve()
            try: dest.relative_to(root.resolve())
            except ValueError:
                inc_errors.append(f'{yp.relative_to(root)}: include escapes root {raw}'); continue
            if not dest.is_file(): inc_errors.append(f'{yp.relative_to(root)}: include missing {raw}')
            elif dest.suffix.lower() in ('.yaml','.yml'):
                try: parse_yaml(dest)
                except Exception as e: inc_errors.append(f'{dest.relative_to(root)}: included YAML {e}')
    check('Include targets are safe, present and parsable',not inc_errors,'; '.join(inc_errors[:8]))
    ev=root/'eval_config.yaml'
    if ev.exists():
        try:
            ec=parse_yaml(ev); evaluation=ec.get('evaluation') if isinstance(ec,dict) else None
            needed={'timeout_seconds','max_tool_calls','max_time_minutes','max_turns'}
            valid=isinstance(evaluation,dict) and needed.issubset(evaluation) and all(isinstance(evaluation[k],(int,float)) and evaluation[k]>0 for k in needed)
            check('eval_config uses evaluation wrapper and four positive limits',valid,str(evaluation))
        except Exception as e: check('eval_config parses',False,repr(e))
    prompt=cfg.get('instruction')
    if isinstance(prompt,IncludeRef):
        path=(agents[0].parent/Path(str(prompt))).resolve()
        if path.is_file():
            txt=path.read_text(encoding='utf-8')
            check('Included instruction has no curly-brace state template',('{' not in txt and '}' not in txt),'')
        else: check('Instruction include exists',False,str(prompt))
def walk_includes(obj):
    if isinstance(obj,IncludeRef): yield None,obj
    elif isinstance(obj,dict):
        for v in obj.values(): yield from walk_includes(v)
    elif isinstance(obj,list):
        for v in obj: yield from walk_includes(v)
if __name__=='__main__': sys.exit(main())
