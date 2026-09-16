from __future__ import annotations
import argparse
import json
import secrets
import sys
import webbrowser
from pathlib import Path
from .errors import RiposteError
from .policy import Policy

def main(argv=None) -> int:
    parser=argparse.ArgumentParser(prog="riposte",description="RIPOSTE · local image security workbench")
    parser.add_argument("--version",action="version",version="RIPOSTE 0.2.0")
    subs=parser.add_subparsers(dest="command",required=True)
    organize=subs.add_parser("organize",help="Read-only plan by default; --apply replaces verified sources.")
    organize.add_argument("root",type=Path)
    organize.add_argument("--apply",action="store_true",help="AUTHORIZE removing successfully migrated source files. No raw backups.")
    organize.add_argument("--discard-sidecars",action="store_true",help="Discard .xmp/.exif/.iptc/.aae and known thumbnail caches on apply.")
    organize.add_argument("--date-mode",choices=["download","modified","embedded"],default="download")
    audit=subs.add_parser("audit");audit.add_argument("root",type=Path)
    listing=subs.add_parser("list");listing.add_argument("root",type=Path)
    serve=subs.add_parser("serve");serve.add_argument("root",type=Path);serve.add_argument("--port",type=int,default=8765);serve.add_argument("--no-browser",action="store_true")
    guard=subs.add_parser("guard");guard.add_argument("root",type=Path);guard.add_argument("image_id");guard.add_argument("--vae",type=Path,action="append",required=True);guard.add_argument("--max-edge",type=int,default=1536);guard.add_argument("--epsilon",type=int,default=4);guard.add_argument("--steps",type=int,default=48);guard.add_argument("--seed",type=int,default=7)
    guard.add_argument("--engine", choices=["encoder", "coupled"], default="coupled")
    guard.add_argument("--pipeline", type=Path, help="Optional local 9-channel inpainting model; coupled engine only.")
    guard.add_argument("--device", choices=["auto", "cpu", "cuda", "mps"], default="auto")
    guard.add_argument("--preserve-white", action=argparse.BooleanOptionalAction, default=True)
    qualify=subs.add_parser("qualify", help="Actual codec views and magnitude-matched controls; encoder evidence only.")
    qualify.add_argument("root", type=Path); qualify.add_argument("trial_id")
    qualify.add_argument("--vae", type=Path, action="append", required=True)
    qualify.add_argument("--device", choices=["auto", "cpu", "cuda", "mps"], default="auto")
    doctor=subs.add_parser("doctor", help="Read-only local runtime and optional model-file preflight.")
    doctor.add_argument("--vae", type=Path)
    upgrade=subs.add_parser("upgrade", help="Explicitly rename legacy application state; artwork is not rewritten.")
    upgrade.add_argument("root", type=Path)
    compare=subs.add_parser("compare");compare.add_argument("root",type=Path);compare.add_argument("image_id");compare.add_argument("candidate",type=Path);compare.add_argument("--max-edge",type=int,default=1536);compare.add_argument("--method",default="external")
    export=subs.add_parser("export");export.add_argument("root",type=Path);export.add_argument("trial_id");export.add_argument("--acknowledge-unverified",action="store_true")
    benchmark=subs.add_parser("benchmark");benchmark.add_argument("root",type=Path);benchmark.add_argument("trial_id");benchmark.add_argument("--model",type=Path,required=True);benchmark.add_argument("--task",choices=["edit","video"],default="edit");benchmark.add_argument("--steps",type=int,default=25)
    challenge=subs.add_parser("challenge", help="Clean/candidate/3-control generation review. Local CUDA baseline, no automatic success score.")
    challenge.add_argument("root", type=Path);challenge.add_argument("trial_id")
    challenge.add_argument("--model", type=Path, required=True)
    challenge.add_argument("--task", choices=["edit", "inpaint", "video"], default="edit")
    challenge.add_argument("--steps", type=int, default=25)
    challenge.add_argument("--seed", type=int, action="append")
    challenge.add_argument("--view", action="append")
    args=parser.parse_args(argv)
    try:
        if args.command=="organize":
            from .organizer import plan,organize
            result=(organize if args.apply else plan)(args.root,Policy(date_mode=args.date_mode,discard_sidecars=args.discard_sidecars))
        elif args.command=="audit":
            from .organizer import audit_workspace
            result=audit_workspace(args.root)
        elif args.command=="list":
            from .store import catalog
            result=catalog(args.root)
        elif args.command=="serve":
            if not 1024<=args.port<=65535:
                raise RiposteError("PORT_INVALID")
            import uvicorn
            from .server import create_app
            app=create_app(args.root)
            url=f"http://127.0.0.1:{args.port}/#token={app.state.token}"
            print("\n RIPOSTE / LOCAL IMAGE SECURITY\n")
            print(" Open this private, local session URL in your browser:\n "+url+"\n")
            print(" No external service. Press Ctrl+C to stop.\n")
            if not args.no_browser:
                # Timer allows socket startup before navigation; no background work after process exit.
                import threading
                timer=threading.Timer(1.5,lambda:webbrowser.open(url));timer.daemon=True;timer.start()
            uvicorn.run(app,host="127.0.0.1",port=args.port,access_log=False,log_level="critical")
            return 0
        elif args.command=="guard":
            from .lab import create_candidate
            result=create_candidate(args.root,args.image_id,args.vae,max_edge=args.max_edge,epsilon=args.epsilon,steps=args.steps,seed=args.seed,
                                    engine=args.engine,pipeline_dir=args.pipeline,device=args.device,preserve_white=args.preserve_white)
        elif args.command=="qualify":
            from .qualification import qualify_trial
            result=qualify_trial(args.root,args.trial_id,args.vae,device=args.device)
        elif args.command=="doctor":
            from .models import runtime_capabilities,inspect_vae
            result={"runtime":runtime_capabilities()}
            if args.vae:
                result["model"]=inspect_vae(args.vae)
        elif args.command=="upgrade":
            from .store import upgrade_workspace
            result=upgrade_workspace(args.root)
        elif args.command=="challenge":
            from .generation import controlled_generation
            result=controlled_generation(args.root,args.trial_id,args.model,args.task,
                seeds=tuple(args.seed or (7,19)), views=tuple(args.view or ("identity","jpeg70")),steps=args.steps)
        elif args.command=="compare":
            from .lab import compare_external
            result=compare_external(args.root,args.image_id,args.candidate,args.max_edge,args.method)
        elif args.command=="export":
            from .lab import export_candidate
            result=export_candidate(args.root,args.trial_id,args.acknowledge_unverified)
        else:
            from .benchmark import run_benchmark
            result=run_benchmark(args.root,args.trial_id,args.model,task=args.task,steps=args.steps)
        print(json.dumps(result,indent=2,allow_nan=False))
        if isinstance(result,dict) and (result.get("checkpoint")=="INCOMPLETE" or result.get("ready") is False):
            return 2
        return 0
    except RiposteError as exc:
        print(json.dumps({"error":exc.code}),file=sys.stderr);return 2
    except KeyboardInterrupt:
        print('{"error":"INTERRUPTED_RESCAN_REQUIRED"}',file=sys.stderr);return 130
    except Exception:
        # Decoder/backend exceptions can contain absolute paths and metadata strings.
        print('{"error":"OPERATION_FAILED"}',file=sys.stderr);return 2

if __name__=="__main__":
    raise SystemExit(main())
