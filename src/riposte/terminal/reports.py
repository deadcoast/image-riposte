"""Authored operation reports shared by the interactive screen and direct CLI.

The normal view explains outcomes; Details is a complete field tree. Raw JSON is
an explicit, syntax-coloured third view. No display path mutates backend data.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import json
import re
import textwrap
from typing import Any
from rich.text import Text
from rich.style import Style
from .surface import ascii_text, PALETTES

@dataclass(frozen=True)
class Run:
    text: str
    role: str = "text"
    bold: bool = False

@dataclass(frozen=True)
class Line:
    runs: tuple[Run, ...] = ()
    @property
    def plain(self): return "".join(run.text for run in self.runs)
    def rich(self, theme="goks"):
        result = Text()
        palette = PALETTES.get(theme, PALETTES["goks"])
        for run in self.runs:
            result.append(run.text, Style(color=palette.get(run.role, "default"), bgcolor="default", bold=run.bold))
        return result

@dataclass
class Report:
    title: str
    outcome: str
    tone: str
    explanation: str
    metrics: list[tuple[str, str]] = field(default_factory=list)
    body: list[Line] = field(default_factory=list)

LABELS = {
    "CPU": "CPU", "CUDA": "CUDA", "Apple MPS": "Apple MPS", "AI evidence": "AI evidence",
    "cpu": "CPU", "cuda": "CUDA", "mps": "Apple MPS",
    "images_to_migrate": "Images to rebuild", "already_clean": "Already clean",
    "sidecars_to_discard": "Sidecars to remove", "sidecars_discarded": "Sidecars removed",
    "migrated": "Images rebuilt", "input_bytes": "Source image data", "remaining": "Unresolved inputs",
    "verified_images": "Clean images verified", "verified_artifacts": "Clean artifacts verified",
    "READY_FOR_REVIEW": "Awaiting review", "ACCEPTED": "Approved", "REJECTED": "Rejected",
    "BLOCKED": "Blocked", "PENDING": "Not processed", "UNVERIFIED": "Unverified",
    "FINISHED": "Queue finished", "OPEN_OR_INTERRUPTED": "Open / interrupted",
    "DATE_ONLY": "Date only", "PUBLICATION_PLAN": "Publishing plan", "APPLY": "Sources replaced",
    "source_clean_sha256": "Clean master fingerprint", "sha256": "SHA-256 fingerprint",
    "artifact_sha256": "Committed image fingerprints", "epsilon_255": "Channel change cap (8-bit)",
    "max_edge": "Maximum publishing edge", "master_changes": "Master images changed",
    "delta_e76_p95": "Colour difference / 95th percentile", "rms_fraction": "Local error fraction",
    "duplicate_renders_avoided": "Duplicate sizes avoided", "finite_gradient": "Finite input gradient",
    "nonzero_gradient": "Nonzero input gradient", "recommended_device": "Detected automatic device",
    "budget_violating_pixels": "Pixels outside allowed budget", "worst_tile_rmse_255": "Worst local-tile error",
}

def label(value: Any) -> str:
    key = str(value)
    return LABELS.get(key, ascii_text(key).replace("_", " ").strip().capitalize())

def scalar(value: Any) -> str:
    if value is None: return "Not reported"
    if isinstance(value, bool): return "Yes" if value else "No"
    if isinstance(value, float): return f"{value:.6g}"
    if isinstance(value, int): return f"{value:,}"
    return ascii_text(value)

def size(value):
    try: count = int(value)
    except (ValueError, TypeError): return scalar(value)
    if count >= 1024**2: return f"{count/1024**2:.2f} MiB"
    if count >= 1024: return f"{count/1024:.1f} KiB"
    return f"{count:,} B"

def role(value):
    if isinstance(value, bool): return "good" if value else "muted"
    if isinstance(value, (int, float)): return "number"
    upper = str(value).upper()
    if any(word in upper for word in ("BLOCKED", "FAILED", "INCOMPLETE", "MISSING", "REJECTED")): return "danger"
    if upper in {"UNVERIFIED", "PENDING", "NOT_OPENED", "OPEN_OR_INTERRUPTED"}: return "warn"
    if upper in {"COMPLETE", "ACCEPTED", "DATE_ONLY", "PASS", "READY_FOR_REVIEW"}: return "good"
    return "value"

def line(text="", colour="text", bold=False):
    return Line((Run(ascii_text(text), colour, bold),))

def fold(value: Line, width: int) -> list[Line]:
    """Word-wrap styled text without losing spans, identifiers, or continuation data."""
    width = max(12, width)
    plain = value.plain
    if not plain: return [Line()]
    pieces = textwrap.wrap(plain, width, replace_whitespace=False, drop_whitespace=False,
                          break_long_words=True, break_on_hyphens=False) or [""]
    result, offset = [], 0
    for piece in pieces:
        end, position, spans = offset + len(piece), 0, []
        for run in value.runs:
            run_end = position + len(run.text)
            low, high = max(offset, position), min(end, run_end)
            if low < high: spans.append(Run(run.text[low-position:high-position], run.role, run.bold))
            position = run_end
        result.append(Line(tuple(spans))); offset = end
    return result

class Writer:
    def __init__(self, width): self.width=max(12,width); self.lines=[]
    def add(self, *runs): self.lines.extend(fold(Line(tuple(runs)), self.width))
    def text(self, text, colour="text", bold=False): self.add(Run(ascii_text(text), colour, bold))
    def blank(self): self.lines.append(Line())
    def section(self, title):
        self.blank(); text=ascii_text(title).upper()
        self.add(Run(text+"  ","label",True),Run("-"*max(0,self.width-len(text)-2),"line"))
    def pair(self, key, value, indent=0):
        key=label(key); indent=min(indent, max(0,self.width//3))
        prefix=" "*indent+key
        pad=max(2,min(30,self.width//2)-len(prefix))
        shown=label(value) if isinstance(value,str) and value in LABELS else scalar(value)
        self.add(Run(prefix+" "*pad,"label"), Run(shown,role(value),True))
    def rows(self, headers, records, weights=None):
        records=list(records)
        if not records: self.text("No records in this section.","muted"); return
        n=len(headers); gap="  "; usable=self.width-2*(n-1)
        weights=weights or [1]*n; widths=[max(3,int(usable*w/sum(weights))) for w in weights]
        widths[-1]=max(3,usable-sum(widths[:-1]))
        def row(values, heading=False):
            columns=[textwrap.wrap(ascii_text(value),widths[i],break_long_words=True,break_on_hyphens=False) or [""] for i,value in enumerate(values)]
            for depth in range(max(map(len,columns))):
                runs=[]
                for i,col in enumerate(columns):
                    content=col[depth] if depth<len(col) else ""
                    runs.append(Run(content.ljust(widths[i]) if i<n-1 else content,"label" if heading else role(values[i]),heading))
                    if i<n-1:runs.append(Run(gap))
                self.add(*runs)
        row(headers,True)
        self.text("-"*self.width,"line")
        for values in records: row(values)


def tree(writer: Writer, data, depth=0):
    """Complete semantic field tree. No truncation or JSON-as-prose fallback."""
    if isinstance(data,dict):
        if not data: writer.text(" "*min(depth*2,18)+"(no fields)","muted")
        for key,value in data.items():
            if isinstance(value,(dict,list,tuple)) and value:
                writer.text(" "*min(depth*2,18)+label(key),"label",True)
                tree(writer,value,depth+1)
            elif isinstance(value,(dict,list,tuple)):writer.pair(key,"None",min(depth*2,18))
            else:writer.pair(key,value,min(depth*2,18))
    elif isinstance(data,(list,tuple)):
        if not data:writer.text("No records.","muted")
        for i,value in enumerate(data,1):
            if isinstance(value,(dict,list,tuple)):
                writer.text(" "*min(depth*2,18)+f"[{i:02d}]","accent",True);tree(writer,value,depth+1)
            else:writer.pair(f"{i:02d}",value,min(depth*2,18))
    else:writer.text(scalar(data),role(data))


def blockers(w, data, operation=""):
    from ..recovery import guidance
    w.section("Needs attention")
    if not data:
        w.text("[CLEAR] No unresolved input blockers were reported.","good"); return
    for code,count in data.items():
        item = guidance(code, operation)
        w.add(Run(f"[! {count}] ","danger",True),Run(item.title,"text",True))
        w.text("Next action: " + item.action,"muted")
        w.text("Code: " + item.code,"code")


def category_destinations(w: Writer, data: dict) -> None:
    from ..recovery import recovery_text
    w.section("Exact destinations / optional categories")
    counts = data.get("counts", {})
    w.pair("Unmatched files", counts.get("unmatched_files", 0))
    w.pair("Ambiguous files", counts.get("ambiguous_files", 0))
    w.pair("Without a category", counts.get("without_category_files", 0))
    w.text("Categories are optional: saved rules, then supported filename patterns. Uncertain titles use date/media/size; existing categories stay.", "muted")
    corpus = data.get("corpus", {})
    if corpus:
        w.pair("Filename patterns", corpus.get("status"))
        w.pair("Distinct title families", corpus.get("normalized_families", 0))
        w.text("Pattern scores measure lexical support, not accuracy. Limited or insufficient analysis never blocks sorting.", "muted")
    for item in data.get("files", []):
        w.text(item["source"], bold=True)
        w.pair("Original title", item.get("original_filename") or "Unknown; sorting still available", 2)
        w.pair("Category", (item.get("category") or {}).get("label", "None; standard date/media/size"), 2)
        if item.get("category_source") == "PRESERVED": w.pair("Category choice", "Existing category retained", 2)
        if item.get("category_source") == "CORPUS": w.pair("Category choice", "Local filename pattern", 2)
        w.pair("Matched terms", ", ".join(item.get("matched_terms", [])) or item.get("match_status", "None"), 2)
        if item.get("match_status") in {"AMBIGUOUS", "ORIGINAL_TITLE_UNAVAILABLE", "UNMATCHED"}:
            w.text(recovery_text(item["match_status"], "sort"), "muted")
        w.pair("Destination", item.get("destination") or item.get("action", "Blocked"), 2)
    w.pair("Preview ID", data.get("plan_id"))
    w.text("Changed files, rules or destinations require a fresh preview.")


def overview(data, command="", width=94) -> Report:
    w=Writer(width)
    r=Report("Operation result","RECORDED","accent","Read the outcome and its next action.")
    if isinstance(data,list):
        r=Report({"list":"Clean image library","publications":"Publishing batches","trials":"Workshop trials",
                  "evaluations":"Saved encoder comparisons","generations":"Saved generation runs"}.get(command,"Saved records"),
                 f"{len(data)} RECORDS","accent","Only the returned selection is shown.")
        if not data:w.text("No records match this selection. Nothing was created by this inspection.","muted")
        elif command=="list" or isinstance(data[0],dict) and "relative" in data[0] and "day" in data[0]:
            r.metrics=[("Clean images",str(len(data)))]
            w.section("Image / canonical names")
            for row in data:
                w.add(Run(row.get('relative',''),"text",True))
                w.add(Run(f"  {row.get('day','')}   ","label"),Run(f"{row.get('width','?')} x {row.get('height','?')} px", "number"))
                w.pair("Image ID",row.get("id",""),2)
        elif command=="publications":
            w.section("Batch / outcome / review")
            for row in data:
                w.add(Run(f"#{row.get('sequence',0):05d}  ","number",True),Run(label(row.get('status','')),"accent",True))
                w.pair("Batch ID",row.get("id",""))
                for key,value in row.get("counts",{}).items():w.pair(key,value,2)
                w.blank()
        else:tree(w,data)
    elif isinstance(data,dict):
        mode=data.get("mode","")
        if mode == "DUPLICATE_SCAN":
            from ..duplicate_review import DuplicateReview
            r = Report("Duplicate Finder", data.get("checkpoint", "INCOMPLETE"), "accent", "Read-only comparison. Files were not sorted, removed or selected for deletion.")
            w.text(data['confidence_policy'], "warn")
            w.section("Scan coverage")
            tree(w, data['counts'])
            if data['issues']['counts']:
                w.section("Incomplete coverage / rescan after resolving")
                tree(w, data['issues'])
            w.section("Findings")
            review = DuplicateReview(data)
            for row in review.rows[:100]:
                w.pair(row['label'], f"{row['confidence']:g} / {row['member_count']} files / {row['basis']}")
                w.text(str(row['left_path']), "text"); w.text(str(row['right_path']), "muted")
            if not review.rows: w.text("No matching files found within the recorded scan coverage.")
            if len(review.rows) > 100: w.text("First 100 findings shown. Use the interactive finder, --json, or --report for all findings.")
            w.section("Comparison boundaries")
            tree(w, data['coverage'])
            if data.get('export'): tree(w, data['export'])
        elif mode == "DUPLICATE_FINDING":
            match = data['finding']
            r = Report(match['label'], str(match['confidence']), "accent", data['confidence_policy'])
            w.section("Comparison evidence")
            tree(w, match)
            for name in ('left', 'right'):
                group = data.get(name)
                if not group: continue
                w.section(f"{name.title()} / {group['count']} files")
                for member in group['members']:
                    w.pair(member['relative'], f"{member['bytes']} bytes / {member['media']}")
                    w.pair("SHA-256", member['sha256'])
                if group['count'] > len(group['members']):
                    w.text("First 50 members shown. Search the finder for any path; JSON export contains every member and fingerprint.")
        elif mode == "TITLE_CATEGORY_DISCOVERY":
            counts = data.get("counts", {})
            r = Report("Filename categories", "READ ONLY" if data.get("checkpoint") == "COMPLETE" else "INCOMPLETE", "accent",
                       "Filename suggestions and session groups only. No files or reusable rules are written.")
            r.metrics = [("Titles analyzed", str(counts.get("analyzed_files", 0))), ("Suggestions", str(data.get("candidate_count", 0))),
                         ("Titles unavailable", str(counts.get("original_title_required", 0)))]
            w.section("Suggestions / matching files")
            w.rows(("Term", "Files", "Example"), [(row["term"], str(row["count"]), row["examples"][0] if row["examples"] else "")
                    for row in data.get("candidates", [])], [3, 1, 5])
            if data.get("omitted_candidates"): w.pair("More suggestions", data["omitted_candidates"])
            if not data.get("candidates"): w.text("No suggestions meet this count. Lower the minimum or enter a category group manually.")
            corpus = data.get("corpus", {})
            w.section("Local filename groups / optional")
            w.pair("Analysis", corpus.get("status", "Not available"))
            for group in corpus.get("categories", []):
                w.pair(group["label"], f"{group['support']} distinct title families")
                w.text(group["label"] + "=" + ";".join(group["terms"]))
            w.text("These literal filename patterns also appear in category-enabled sort previews. Editing and saving a rule is optional.", "muted")
            review = data.get("review", {})
            w.section("Category groups / session draft")
            for group in review.get("categories", []):
                w.pair(group["label"], f"{group['count']} files / " + " | ".join(group["terms"]))
            if review.get("categories"):
                w.pair("Unmatched files", counts.get("unmatched_files", 0))
                w.pair("Ambiguous files", counts.get("ambiguous_files", 0))
                for overlap in review.get("overlaps", []): w.pair(" / ".join(overlap["categories"]), overlap["count"])
            w.text("Return to edit Category groups: Hockey=hockey;goalie. Use commas between groups. Clear a group to remove it.")
            w.text("Numbered names are excluded from suggestions; they can still sort without a category. Details shows match evidence. Media contents were not validated.", "muted")
            if data.get("checkpoint") == "INCOMPLETE": w.text("Some paths could not be scanned; counts are incomplete.", "warn")
        elif mode == "CATEGORY_RULES":
            r = Report("Saved category rules", data.get("status", "STORED"), "accent", "Rules are reusable. Sorting requires its own preview and confirmation.")
            for rule in data.get("rules", {}).get("categories", []):
                w.section(rule["label"])
                for key in ("slug", "terms", "exclusions", "priority"): w.pair(key, rule[key])
            w.pair("Revision", data.get("revision"))
            if data.get("status") == "DRAFT": w.text("Press s to review SAVE confirmation, or return to edit the draft.")
            tree(w, data.get("review"))
        elif mode in {"SORT_RIPOSTE_PLAN", "SORT_RIPOSTE_RESULT"}:
            preview = mode == "SORT_RIPOSTE_PLAN"
            sorting = data.get("sorting", {})
            r = Report("Sort + RIPOSTE", "READ ONLY" if preview else "INCOMPLETE", "accent" if preview and data.get("ready") else "warn",
                       "Confirm source replacement before sorting; protection follows only after sorting succeeds." if preview else "The combined workflow stopped. Completed sorting is retained.")
            w.section("Sorting")
            tree(w, sorting.get("counts", {}))
            w.text("Sort images and videos separately; protect images only. Original copies are retained privately for undo.", "warn")
            blockers(w, sorting.get("blockers", {}), "sort")
            if sorting.get("category_sorting"):
                category_destinations(w, sorting)
            w.section("Protection")
            if preview:
                w.text("Protect all matching organized images, including new additions." if data.get("selection") == "ALL_MATCHING_AFTER_SORT" else "Protect only the selected catalog images after sorting.")
            else:
                w.text(str(data.get("protection", "NOT_STARTED")))
            if preview: tree(w, data.get("recipe", {}))
            if data.get("code"): w.pair("Stopped because", data["code"])
            if data.get("recovery"): w.text(data["recovery"])
        elif mode in {"UNDO_SORT_PREVIEW", "UNDO_SORT"}:
            preview = mode == "UNDO_SORT_PREVIEW"
            r = Report("Undo last sort", "READ ONLY" if preview else data.get("checkpoint", "INCOMPLETE"),
                       "good" if data.get("ready") else "warn", "Restore original names, bytes and modified times. Original metadata returns too.")
            w.pair("Files to restore", data.get("files_to_restore", 0))
            w.pair("Sorted copies to remove", data.get("outputs_to_remove", 0))
            w.text("Conflicts block undo. Protection outputs and review records stay in place.")
            w.text("Sorts made before recovery history was introduced cannot be undone.")
            blockers(w, data.get("blockers", {}), command)
        elif mode in {"READ_ONLY","APPLY"}:
            preview=mode=="READ_ONLY";counts=data.get("counts",{});blocked=data.get("blockers",{})
            r=Report("Migration plan" if preview else "Clean & organize", "READ ONLY" if preview else data.get("checkpoint","RECORDED"),
                     "warn" if blocked else "good", "No files have been changed." if preview else "Verified sources were replaced; unsuccessful inputs remain.")
            planned = counts.get("files_to_sort", sum(counts.get(k, 0) for k in ("images_to_migrate", "images_to_relocate", "videos_to_sort")))
            applied = sum(counts.get(k, 0) for k in ("migrated", "relocated", "videos_sorted"))
            r.metrics=[("To sort" if preview else "Sorted",str(planned if preview else applied)),
                       ("Already sorted",str(counts.get("already_sorted", counts.get("already_clean",0) + counts.get("already_sorted_videos",0)))),("Blockers",str(sum(blocked.values())))]
            w.section("What this operation does" if preview else "Source replacement receipt")
            w.text("Reconstruct date-only PNGs, classify by date and resolution, then name them consistently.")
            w.text("Images go into img; videos into vid. Videos keep all bytes and metadata; protection is image-only.")
            w.text("Private undo history retains original files, names and metadata and uses extra disk space.","warn")
            for key,value in counts.items(): w.pair(key,size(value) if key=="input_bytes" else value)
            if data.get("destinations"):
                w.section("Calendar / output routes")
                w.rows(("Destination","Files"),[(folder,str(count)) for folder,count in data["destinations"].items()],[5,1])
            blockers(w,blocked,command)
            if data.get("category_sorting"):
                category_destinations(w, data)
            if "remaining_unmanaged_inputs" in data:w.pair("Remaining unmanaged inputs",data["remaining_unmanaged_inputs"])
        elif mode=="PUBLICATION_PLAN":
            r=Report("Publishing plan","READ ONLY","good","Each final size is optimized independently. Clean masters remain unchanged.")
            r.metrics=[("Images",str(data.get("images",0))),("Final outputs",str(data.get("outputs",0))),
                       ("Duplicate sizes skipped",str(data.get("duplicate_renders_avoided",0)))]
            if data.get("source_mode") == "snapshot":
                w.text("Original files and folders stay unchanged. Clean snapshots support later resume and review.")
                w.pair("Non-image files left untouched", data.get("ignored_files", 0))
            w.section("Final-size jobs")
            w.rows(("Job","Date","Edge limit","Clean image ID"),
                   [(str(t.get("index",n)+1),t.get("date",""),f"{t.get('max_edge','?')} px",t.get("image_id","")) for n,t in enumerate(data.get("tasks",[]))],[1,2,2,5])
            w.text("Edge limits never enlarge a smaller source; actual dimensions follow the master.","muted")
            w.section("Protection settings")
            recipe=data.get("recipe",{}); guard=recipe.get("guard",{}); quality=recipe.get("quality",{})
            if recipe.get("edges"):w.pair("Final edge limits",", ".join(f"{value:,} px" for value in recipe["edges"]))
            if guard:w.pair("Search",f"{guard.get('steps','?')} iterations x {guard.get('restarts','?')} restarts")
            if "epsilon_255" in quality:w.pair("Pixel change budget",f"At most {quality['epsilon_255']} of 255 channel levels")
            if "preserve_white" in quality:w.pair("Preserve smooth white",quality["preserve_white"])
            if "delta_e76_p95" in quality:w.pair("Colour-difference limit",quality["delta_e76_p95"])
            w.text("Every model and quality parameter remains available in Details.","muted")
            w.section("Next action")
            w.text("Start protection with this selection and these settings. Models must be available locally.")
            w.text("A completed render is a candidate, not a demonstrated AI-resistance result.","warn")
        elif mode=="PUBLICATION_BATCH":
            counts=data.get("counts",{})
            r=Report("Publishing batch",label(data.get("status","OPEN")).upper(),"warn" if counts.get("BLOCKED") else "accent",
                     "Queue completion and output approval are separate states.")
            r.metrics=[("Awaiting review",str(counts.get("READY_FOR_REVIEW",0))), ("Approved",str(counts.get("ACCEPTED",0))),
                       ("Blocked",str(counts.get("BLOCKED",0)))]
            w.pair("Batch ID",data.get("id"));w.section("Output queue")
            for n,item in enumerate(data.get("items",[]),1):
                w.add(Run(f"{n:02d}  ","number"),Run(label(item.get("status","")),role(item.get("status")),True),Run("  /  "),Run(label(item.get("review","PENDING")),role(item.get("review"))))
                w.pair("Output ID",item.get("id"),2)
                if item.get("width"):w.pair("Dimensions",f"{item['width']} x {item['height']} px",2)
                if item.get("code"):w.pair("Blocker",item["code"],2)
                w.blank()
            w.text("Open an output to inspect exact pixels, record approval, then package approved images.","muted")
        elif data.get("contents")=="APPROVED_DATE_ONLY_PNGS" or command in {"package","export"}:
            approved=command!="export"
            r=Report("Approved image pack" if approved else "Expert trial export","WRITTEN","good",
                     "Approved candidate PNG bytes only. No clean baselines or research reports." if approved else "Expert export; not the reviewed publishing-pack route.")
            r.metrics=[("Archive size" if approved else "File size",size(data.get("bytes",0))), ("Metadata","Date only")]
            w.section("Saved file")
            w.pair("Workspace-relative file",data.get("relative","Not reported"))
            if "sha256" in data:w.pair("sha256",data["sha256"])
            if approved:
                w.section("Included / excluded")
                w.text("[+] Approved PNGs in calendar / month / size folders","good")
                w.text("[-] Raw originals, clean comparisons, models and reports","muted")
                w.text("The packed PNG bytes are unchanged from the approved candidates.")
            w.section("Next action");w.text("Use this file for distribution. Later review changes affect future packs only.")
        elif "checkpoint" in data:
            r=Report("Workspace audit",data["checkpoint"],"good" if data["checkpoint"]=="COMPLETE" else "warn",
                     "This checks image containers and organization, not resistance to AI reuse.")
            r.metrics=[("Clean images",str(data.get("verified_images",0))), ("Clean artifacts",str(data.get("verified_artifacts",0))),
                       ("Blockers",str(sum(data.get("blockers",{}).values())))]
            w.section("Verified scope");w.pair("Metadata policy",data.get("metadata_policy","Not reported"))
            blockers(w,data.get("blockers",{}),command)
        elif "runtime" in data or command=="doctor":
            rt=data.get("runtime",{})
            r=Report("Local processing runtime","INSPECTED","accent","Device and package availability are shown separately from model execution.")
            if rt:
                r.metrics=[("CPU","Available" if rt.get("cpu") else "Unavailable"), ("CUDA","Available" if rt.get("cuda") else "Unavailable"),
                           ("Apple MPS","Available" if rt.get("mps") else "Unavailable")]
                w.section("Packages")
                w.rows(("Package","Installed version"),list(rt.get("versions",{}).items()),[2,3])
                if rt.get("missing"):
                    w.section("Missing optional packages");w.text(", ".join(rt["missing"]),"warn")
                    w.text("Install the [lab] extra for model processing; cleaning does not need these models.","muted")
                w.pair("recommended_device",rt.get("recommended_device"))
            rest={k:v for k,v in data.items() if k!="runtime"}
            if rest:w.section("Model execution / selection");tree(w,rest)
            else:w.text("No model execution was requested.","muted")
        elif mode in {"CLEAN_IMAGE","VERIFIED_IMAGE"}:
            r=Report("Clean image" if mode=="CLEAN_IMAGE" else "Verified image","AUDITED","good","Container audit and pixel identity were checked before this result.")
            r.metrics=[("Dimensions",f"{data.get('width','?')} x {data.get('height','?')}"),("Date",str(data.get("day",data.get("date","Not reported"))))]
            w.section("Image identity")
            for key in ("relative","id","day","mode","bytes","sha256","viewer"):
                if key in data:w.pair(key,size(data[key]) if key=="bytes" else data[key])
            if data.get("audit"):w.section("Container checks");tree(w,data["audit"])
        else:
            titles={"qualify":"Encoder comparison", "guard":"Standalone candidate", "compare":"Imported candidate", "trials":"Workshop trial",
                    "challenge":"Five-arm generation", "generation":"Generation report", "benchmark":"Paired generation",
                    "evaluations":"Saved comparisons", "handoff":"Exact-file workshop handoff", "frame":"Generation frame", "upgrade":"Workspace state upgrade"}
            r.title=titles.get(command,"Operation record")
            if command in {"qualify","guard","compare","challenge","benchmark","trials","handoff"}:
                r.explanation="Optional workshop evidence; not a protection certificate."
            tree(w,data)
    else:tree(w,data)
    r.body=w.lines
    return r

_JSON=re.compile(r'"(?:\\.|[^"\\])*"|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|true|false|null|[{}\[\]:,]|\s+|.',re.S)

def raw_lines(data, width):
    text=json.dumps(data,indent=2,ensure_ascii=True,allow_nan=False)
    result=[]
    for raw in text.splitlines():
        spans=[]
        for match in _JSON.finditer(raw):
            token=match.group(); colour="muted"
            if token.startswith('"'):colour="label" if raw[match.end():].lstrip().startswith(':') else "value"
            elif token in {"true","false","null"}:colour="code"
            elif token and token[0] in '-0123456789':colour="number"
            spans.append(Run(token,colour))
        result.extend(fold(Line(tuple(spans)),width))
    return result


def report_lines(report, data, view, width):
    if view=="json":return raw_lines(data,width)
    w=Writer(width)
    if view=="details":
        w.section("Complete field record");tree(w,data);return w.lines
    spans=[]
    for index,(key,value) in enumerate(report.metrics):
        if index:spans.append(Run("   |   ","line"))
        spans.extend((Run(str(value),"number",True),Run(" "+key,"label")))
    if spans:w.add(*spans)
    return w.lines+report.body


def paint_lines(surface, lines, x, y, width, height, scroll=0):
    capacity=max(1,height); scroll=min(max(0,scroll),max(0,len(lines)-capacity))
    for row,record in enumerate(lines[scroll:scroll+capacity]):
        col=x
        for run in record.runs:
            remaining=x+width-col
            if remaining<=0:break
            surface.text(col,y+row,run.text,run.role,bold=run.bold,width=remaining)
            col+=len(run.text)
    return scroll,min(len(lines),scroll+capacity)
