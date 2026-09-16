#!/usr/bin/env python3
"""Create figures and the complete algorithm table for the major-revision draft."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT.parent / "over-leaf"
ANALYSIS = json.loads((ROOT / "data/results/paper-major-revision-analysis.json").read_text())
VALIDATION = json.loads((ROOT / "data/results/paper-final-statistical-validation.json").read_text())
ROWS = list(csv.DictReader((ROOT / "data/results/batch-paper-final-19-algorithms-summary.csv").open()))
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"


def font(size: int, bold: bool = False): return ImageFont.truetype(FONT_BOLD if bold else FONT, size)


def base(title: str, subtitle: str):
    image=Image.new("RGB",(1800,1100),"white");draw=ImageDraw.Draw(image)
    draw.text((85,42),title,fill="#172033",font=font(40,True));draw.text((85,96),subtitle,fill="#667085",font=font(23));return image,draw


def resource_figure():
    image,draw=base("Which resource components carry the association?","Spearman correlation with PL-Exp mean LLR at n = 4096; 19 algorithms")
    data=ANALYSIS["resource_decomposition_by_n"][-1]["correlations"];labels=["Comparisons c","Movements w","Storage s","c + w","c + s","w + s","c + w + s"]
    keys=["c","w","s","c+w","c+s","w+s","c+w+s"]
    left,top,right,bottom=480,180,1660,970;x0=left+(0.4/1.2)*(right-left)
    for tick in [-.4,-.2,0,.2,.4,.6,.8]:
        x=left+((tick+.4)/1.2)*(right-left);draw.line((x,top,x,bottom),fill="#e4e7ec",width=2);draw.text((x-22,bottom+15),f"{tick:.1f}",fill="#344054",font=font(20))
    for i,(label,key) in enumerate(zip(labels,keys)):
        y=top+45+i*105;v=data[key];x=left+((v+.4)/1.2)*(right-left);color="#1769aa" if key=="c+w+s" else ("#c62828" if v<0 else "#546e7a")
        draw.text((80,y-17),label,fill="#172033",font=font(27, key=="c+w+s"));draw.rectangle((min(x,x0),y-20,max(x,x0),y+20),fill=color);draw.text((x+12 if v>=0 else x-82,y-17),f"{v:.3f}",fill=color,font=font(24,True))
    draw.line((x0,top,x0,bottom),fill="#344054",width=3);image.save(PAPER/"figures/resource-decomposition.png",dpi=(180,180))


def finite_size_figure():
    image,draw=base("Fitted exponent approaches the random-BST prediction","Optimized-cutoff aggregate fits; 1,000 executions per cell")
    names={"quick":"Historical Hoare Quick","tree-unbalanced":"Unbalanced BST","tree-avl":"AVL tree"};colors={"quick":"#1769aa","tree-unbalanced":"#2e7d32","tree-avl":"#ef6c00"};box=(220,180,1650,920);sizes=[128,256,512,1024,2048,4096]
    for y in [2,2.2,2.4,2.6]:
        py=box[3]-(y-1.9)/.8*(box[3]-box[1]);draw.line((box[0],py,box[2],py),fill="#e4e7ec",width=2);draw.text((150,py-13),f"{y:.1f}",fill="#344054",font=font(21))
    for i,n in enumerate(sizes):
        x=box[0]+i/(len(sizes)-1)*(box[2]-box[0]);draw.text((x-35,box[3]+18),str(n),fill="#344054",font=font(21))
    theoretical=box[3]-(2-1.9)/.8*(box[3]-box[1]);draw.line((box[0],theoretical,box[2],theoretical),fill="#111827",width=3)
    draw.text((box[0]+15,theoretical-36),"subtree-size prediction alpha = 2",fill="#111827",font=font(20,True))
    for index,(name,label) in enumerate(names.items()):
        rows=sorted((r for r in ANALYSIS["finite_size_diagnostics"] if r["algorithm"]==name),key=lambda r:r["n"]);points=[]
        for i,row in enumerate(rows): points.append((box[0]+i/(len(rows)-1)*(box[2]-box[0]),box[3]-(row["alpha"]-1.9)/.8*(box[3]-box[1])))
        draw.line(points,fill=colors[name],width=6)
        for x,y in points: draw.ellipse((x-9,y-9,x+9,y+9),fill=colors[name])
        draw.line((1120,210+index*42,1180,210+index*42),fill=colors[name],width=6);draw.text((1195,196+index*42),label,fill=colors[name],font=font(22,True))
    draw.text((760,995),"Input size n",fill="#172033",font=font(26));draw.text((75,520),"Fitted alpha",fill="#172033",font=font(26));image.save(PAPER/"figures/finite-size-alpha.png",dpi=(180,180))


def block_figure():
    image,draw=base("Association across independent execution blocks","Twenty non-overlapping blocks of 50 matched seeds at n = 4096")
    rows=ANALYSIS["block_design"]["correlations"];box=(210,180,1650,920);ymin,ymax=.68,.82
    for y in [.68,.72,.76,.80]:
        py=box[3]-(y-ymin)/(ymax-ymin)*(box[3]-box[1]);draw.line((box[0],py,box[2],py),fill="#e4e7ec",width=2);draw.text((135,py-12),f"{y:.2f}",fill="#344054",font=font(21))
    points=[]
    for i,row in enumerate(rows):
        x=box[0]+i/(len(rows)-1)*(box[2]-box[0]);y=box[3]-(row["spearman"]-ymin)/(ymax-ymin)*(box[3]-box[1]);points.append((x,y));draw.ellipse((x-8,y-8,x+8,y+8),fill="#1769aa");draw.text((x-8,box[3]+18),str(i+1),fill="#344054",font=font(17))
    draw.line(points,fill="#1769aa",width=4);summary=ANALYSIS["block_design"]["correlation_summary"]
    draw.text((270,990),f"Range {summary['minimum']:.3f}-{summary['maximum']:.3f}; median {summary['median']:.3f}",fill="#172033",font=font(27,True));draw.text((810,1030),"Seed block",fill="#172033",font=font(24));image.save(PAPER/"figures/block-correlations.png",dpi=(180,180))


def algorithm_table():
    tail={row["algorithm"]:row for row in VALIDATION["tail_validation"]};rows=[row for row in ROWS if row["n"]=="4096"]
    labels={"binary-insertion":"Binary insertion","bitonic-network":"Bitonic network","bubble":"Bubble","heap":"Heap","insertion":"Insertion","introsort":"Introsort","merge-bottom-up":"Merge bottom-up","merge-insertion":"Merge insertion","merge-top-down":"Merge top-down","odd-even-merge-network":"Odd-even network","quick":"Quick (Hoare)","quick-dual-pivot":"Quick dual-pivot","quick-median-three":"Quick median-3","quick-random":"Quick deterministic","selection":"Selection","shell":"Shell","tournament":"Tournament","tree-avl":"AVL tree","tree-unbalanced":"Unbalanced BST"}
    lines=[r"\begin{landscape}",r"\begin{longtable}{lrrrrrrrrrrr}",r"\caption{Complete results at $n=4096$. LLR columns are mean log-likelihood differences per tail observation.}\label{tab:complete-results}\\",r"\toprule",r"Algorithm & $c$ & $w$ & $s$ & $\eta$ & $P_{80}$ & $x_{\min}$ & $\hat\alpha$ & tail \% & PL--Exp & PL--LN & $p_{boot}$\\",r"\midrule\endfirsthead",r"\toprule",r"Algorithm & $c$ & $w$ & $s$ & $\eta$ & $P_{80}$ & $x_{\min}$ & $\hat\alpha$ & tail \% & PL--Exp & PL--LN & $p_{boot}$\\",r"\midrule\endhead"]
    for row in rows:
        t=tail[row["algorithm"]];lines.append(f"{labels[row['algorithm']]} & {float(row['normalized_excess_comparisons_mean']):.3f} & {float(row['movements_per_node_mean']):.1f} & {float(row['peak_auxiliary_storage_fraction_mean']):.3f} & {float(row['combined_efficiency_equal_weights_mean']):.4f} & {100*float(row['degree_p80_fraction_mean']):.1f} & {t['xmin']} & {t['alpha']:.2f} & {100*t['tail_fraction']:.2f} & {t['power_vs_exponential_llr_per_observation']:.3f} & {t['power_vs_lognormal_llr_per_observation']:.4f} & {t['power_law_bootstrap_p']:.3f}\\\\")
    lines += [r"\bottomrule",r"\end{longtable}",r"\end{landscape}"]
    (PAPER/"tables").mkdir(exist_ok=True);(PAPER/"tables/algorithm-results.tex").write_text("\n".join(lines)+"\n")


def main():
    (PAPER/"figures").mkdir(exist_ok=True);resource_figure();finite_size_figure();block_figure();algorithm_table();print("wrote major-revision figures and table")


if __name__=="__main__":main()
