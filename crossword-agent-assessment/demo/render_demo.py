#!/usr/bin/env python3
"""Render the demo as reproducible, code-driven motion graphics (no external assets)."""
from __future__ import annotations
import math, os, shutil, subprocess, sys
from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "demo" / "crossword-agent-demo-silent.mp4"
W, H, FPS, DURATION = 1280, 720, 24, 54
BG = (8, 15, 28)
PANEL = (17, 29, 48)
PANEL2 = (22, 38, 61)
WHITE = (237, 244, 252)
MUTED = (151, 170, 194)
TEAL = (63, 224, 190)
BLUE = (111, 145, 255)
AMBER = (255, 196, 91)
RED = (255, 117, 117)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

@lru_cache(maxsize=None)
def font(size, bold=False):
    candidates = [
        BOLD if bold else FONT,
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default(size=size)

def ease(x):
    x = max(0.0, min(1.0, x))
    return x*x*(3-2*x)

def rounded(draw, box, fill, outline=None, radius=18, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)

def label(draw, xy, text, size=18, color=MUTED, bold=False, anchor=None):
    draw.text(xy, text, font=font(size, bold), fill=color, anchor=anchor)

def centered(draw, x, y, text, size=24, color=WHITE, bold=False):
    label(draw, (x, y), text, size, color, bold, "mm")

def wrapped(draw, xy, text, width, size=22, color=WHITE, bold=False, spacing=6):
    f = font(size, bold)
    words = text.split()
    lines=[]; line=""
    for word in words:
        trial = (line + " " + word).strip()
        if draw.textlength(trial, font=f) > width and line:
            lines.append(line); line=word
        else: line=trial
    if line: lines.append(line)
    x,y=xy
    for row in lines:
        draw.text((x,y),row,font=f,fill=color)
        y += size + spacing
    return y

def background(t):
    im=Image.new("RGB",(W,H),BG)
    d=ImageDraw.Draw(im,"RGB")
    # Restrained ambient shapes and top rule keep visual texture quiet.
    d.ellipse((920,-330,1510,260), fill=(11,26,47))
    d.ellipse((-430,500,210,1140), fill=(10,23,39))
    d.rectangle((0,0,W,4),fill=TEAL)
    d.line((72,82,W-72,82),fill=(33,50,73),width=1)
    label(d,(74,43),"CROSSWORD AGENT",17,TEAL,True)
    label(d,(W-74,44),"ASSESSMENT DEMO  /  2026",14,MUTED,True,"ra")
    # Footer timeline.
    d.line((72,H-52,W-72,H-52), fill=(38,55,77), width=2)
    d.line((72,H-52,72+(W-144)*t/DURATION,H-52), fill=TEAL, width=3)
    label(d,(74,H-31),"HYBRID REASONING  •  CROSSINGS AS CONSTRAINTS",12,MUTED,True)
    label(d,(W-74,H-31),f"{int(t):02d} / {DURATION:02d} SEC",12,MUTED,True,"ra")
    return im,d

def board(draw,x,y,cell,t,start=17.0):
    words=["BALL","AREA","LEAD","LADY"]
    progress=max(0.0,min(1.0,(t-start)/8.0))
    shown=int(progress*16)
    for idx in range(16):
        r,c=divmod(idx,4); xx=x+c*cell; yy=y+r*cell
        active=idx<shown
        fill=(25,58,72) if active else (23,36,55)
        edge=TEAL if idx==shown and shown<16 else (51,75,101)
        rounded(draw,(xx,yy,xx+cell-7,yy+cell-7),fill,edge,10,2 if idx==shown and shown<16 else 1)
        if active:
            ch=words[r][c]
            centered(draw,xx+(cell-7)/2,yy+(cell-7)/2,ch,36,WHITE,True)
        elif idx<min(16,shown+4):
            centered(draw,xx+(cell-7)/2,yy+(cell-7)/2,"·",27,(76,102,130),False)

def scene(t,im,d):
    if t < 6:
        # Opening client framing.
        rounded(d,(78,135,1202,565),PANEL,(41,63,88),24)
        label(d,(128,192),"A PRACTICAL AI SOLVER",16,TEAL,True)
        label(d,(126,243),"Crossword answers,",52,WHITE,True)
        label(d,(126,306),"checked at every crossing.",52,WHITE,True)
        wrapped(d,(130,402),"Language-model reasoning, bounded by deterministic grid constraints.",790,24,MUTED)
        for i,txt in enumerate(["CLUE", "CANDIDATES", "CROSSINGS", "FILL"]):
            xx=130+i*252
            rounded(d,(xx,492,xx+206,538),PANEL2,(44,70,97),12)
            centered(d,xx+103,515,txt,15,TEAL if i<3 else WHITE,True)
            if i<3: label(d,(xx+218,508),"→",21,MUTED,True)
    elif t < 15:
        label(d,(88,123),"01  /  THE PIPELINE",15,TEAL,True)
        label(d,(88,156),"Reasoning, then verification",35,WHITE,True)
        labels=[("01","Parse grid","Number Across / Down entries"),("02","Generate candidates","Rank clue answers with a model"),("03","Propagate constraints","Reject crossing-letter conflicts"),("04","Search & solve","MRV + bounded backtracking")]
        for i,(num,title,desc) in enumerate(labels):
            y=232+i*82
            active=t >= 7.0+i*1.8
            fill=(21,52,65) if active else PANEL
            border=TEAL if active else (43,62,85)
            rounded(d,(104,y,1172,y+64),fill,border,15,2 if active else 1)
            centered(d,148,y+32,num,18,TEAL if active else MUTED,True)
            label(d,(194,y+9),title,20,WHITE,True)
            label(d,(532,y+13),desc,17,MUTED)
            if i<3:
                d.line((148,y+64,148,y+80),fill=(49,86,107),width=2)
    elif t < 27:
        label(d,(88,123),"02  /  LIVE SOLVE",15,TEAL,True)
        label(d,(88,156),"Eight entries. One consistent fill.",34,WHITE,True)
        board(d,116,235,112,t,17.0)
        rounded(d,(636,230,1164,579),PANEL,(42,64,87),18)
        label(d,(675,266),"CROSSING CHECKS",14,TEAL,True)
        rows=[("1A","BALL","sports object"),("5A","AREA","region of space"),("6A","LEAD","guide / go first"),("7A","LADY","courteous address")]
        for i,(eid,ans,desc) in enumerate(rows):
            y=310+i*60
            done=t>19+i*1.15
            rounded(d,(674,y,1124,y+45),(22,55,63) if done else PANEL2,None,9)
            label(d,(692,y+12),eid,15,TEAL,True)
            label(d,(752,y+8),ans if done else "····",22,WHITE,True)
            label(d,(870,y+13),desc,14,MUTED)
        rounded(d,(674,558,1124,583),(20,58,52),None,9)
        label(d,(692,563),"ALL SHARED LETTERS AGREE",12,TEAL,True)
    elif t < 31:
        label(d,(88,123),"03  /  CONFLICT RESOLUTION",15,TEAL,True)
        label(d,(88,156),"Crossings act as hard evidence",34,WHITE,True)
        rounded(d,(102,234,1178,558),PANEL,(42,64,87),20)
        # Crossing pattern / competing candidates.
        label(d,(154,276),"CLUE",13,MUTED,True)
        label(d,(154,301),"A region measured on a map",23,WHITE,True)
        label(d,(154,360),"CROSSING PATTERN",13,MUTED,True)
        for i,ch in enumerate("A R E A".split()):
            xx=154+i*73
            rounded(d,(xx,391,xx+57,450),(24,63,73),(57,138,130),9,1)
            centered(d,xx+28,420,ch,24,TEAL,True)
        rounded(d,(620,272,1078,346),(53,35,43),(125,62,66),12)
        label(d,(647,288),"IDEA",24,RED,True)
        label(d,(748,294),"rejected: crossing mismatch",16,MUTED)
        rounded(d,(620,377,1078,451),(20,56,54),(54,133,119),12)
        label(d,(647,393),"AREA",24,TEAL,True)
        label(d,(748,399),"kept: all letters supported",16,WHITE)
        label(d,(154,496),"The clue suggests meaning; the grid decides consistency.",20,MUTED)
    elif t < 43:
        label(d,(88,123),"04  /  BENCHMARK",15,TEAL,True)
        label(d,(88,156),"Constraint recovery under noisy rankings",32,WHITE,True)
        # Baseline / agent comparison cards.
        metrics=[("TOP-CHOICE BASELINE","0 / 22","full solves",RED,0.0),
                 ("CROSSWORD AGENT","22 / 22","full solves",TEAL,1.0)]
        for i,(title,value,caption,color,ratio) in enumerate(metrics):
            x=105+i*554
            rounded(d,(x,232,x+505,500),PANEL,(45,67,91),18)
            label(d,(x+30,268),title,14,MUTED,True)
            label(d,(x+30,320),value,48,color,True)
            label(d,(x+254,346),caption,17,MUTED)
            rounded(d,(x+30,405,x+465,428),(34,51,70),None,10)
            if ratio: rounded(d,(x+30,405,x+465*ratio+30,428),color,None,10)
            label(d,(x+30,454),"0% exact words" if i==0 else "100% exact words",16,color,True)
        label(d,(112,536),"22 seeded synthetic puzzles  •  152 clue entries  •  0 crossing violations after CSP",16,MUTED)
        label(d,(112,564),"Scope: tiny word-square fixtures — not a claim of real-world clue accuracy.",15,AMBER,True)
    else:
        label(d,(88,123),"05  /  NEXT EVALUATION",15,TEAL,True)
        label(d,(88,160),"A credible quality gate",37,WHITE,True)
        rounded(d,(100,235,1178,508),PANEL,(42,64,87),19)
        steps=[("01","100+ held-out licensed crosswords"),("02","Candidate recall, word & letter accuracy"),("03","Latency, tokens, cost, and failure review")]
        for i,(num,txt) in enumerate(steps):
            y=283+i*66
            rounded(d,(138,y,1066,y+48),PANEL2,(45,69,94),10)
            centered(d,170,y+24,num,15,TEAL,True)
            label(d,(211,y+11),txt,20,WHITE,True)
        label(d,(140,472),"Provider-neutral adapter  •  deterministic solver  •  measurable trade-offs",16,MUTED)
        label(d,(102,552),"Thank you.",25,TEAL,True)

def caption(t,d):
    captions=[(0,3.0,"Hello, and thanks for joining."),
              (3.0,7.0,"Transparent, testable crossword reasoning."),
              (7.0,11.0,"Grid parsing numbers Across and Down entries."),
              (11.0,16.0,"A configurable model ranks clue-answer candidates."),
              (16.0,22.0,"Answer length and crossing letters are hard constraints."),
              (22.0,27.0,"Arc consistency prunes; bounded backtracking can search."),
              (27.0,32.0,"Eight entries resolve to one consistent, complete grid."),
              (32.0,41.0,"22 synthetic puzzles: top-choice baseline 0/22; agent 22/22."),
              (41.0,45.0,"Constraint recovery only—not real-world clue accuracy."),
              (45.0,51.0,"Next: held-out crosswords, measured model quality, latency, and cost."),
              (51.0,54.0,"Provider-neutral. Measurable. Built to improve.")]
    text=next((c for a,b,c in captions if a<=t<b),"")
    if text:
        rounded(d,(96,604,1184,667),(13,24,39),(38,61,85),12)
        centered(d,640,635,text,18,WHITE,False)

def frame(t):
    im,d=background(t)
    scene(t,im,d)
    caption(t,d)
    return im

def main():
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        try:
            import imageio_ffmpeg
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        except (ImportError, RuntimeError) as exc:
            raise SystemExit(
                "FFmpeg is unavailable. Install the demo dependencies with "
                "python3 -m pip install -r demo/requirements.txt"
            ) from exc
    OUT.parent.mkdir(parents=True,exist_ok=True)
    cmd=[ffmpeg,"-y","-loglevel","error","-f","rawvideo","-pixel_format","rgb24","-video_size",f"{W}x{H}","-framerate",str(FPS),"-i","-","-an","-c:v","libx264","-preset","ultrafast","-crf","20","-pix_fmt","yuv420p","-movflags","+faststart",str(OUT)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    try:
        for i in range(FPS*DURATION):
            im=frame(i/FPS)
            proc.stdin.write(im.tobytes())
            if i % (FPS*8)==0: print(f"rendered {i//FPS}/{DURATION}s",flush=True)
        proc.stdin.close()
        code=proc.wait()
        if code: raise SystemExit(code)
    except BaseException:
        if proc.stdin and not proc.stdin.closed: proc.stdin.close()
        proc.terminate(); raise
    print(OUT)

if __name__=="__main__": main()
