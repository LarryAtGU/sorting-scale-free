#!/usr/bin/env python3
"""Create publication PNG figures from the frozen summary and validation output."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "data/results/batch-paper-final-19-algorithms-summary.csv"
VALIDATION = ROOT / "data/results/paper-final-statistical-validation.json"
OUTPUT = ROOT.parent / "over-leaf/figures"
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
COLORS = {"pivot": "#1769aa", "tree": "#2e7d32", "merge": "#8e24aa", "network": "#ef6c00", "other": "#546e7a"}


def font(size: int, bold: bool = False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT, size)


def canvas(title: str):
    image = Image.new("RGB", (1800, 1100), "white")
    draw = ImageDraw.Draw(image)
    draw.text((90, 38), title, fill="#172033", font=font(40, True))
    draw.text((90, 91), "Degree distributions aggregate 1,000 executions per algorithm–size cell.", fill="#667085", font=font(24))
    return image, draw


def axes(draw, box, xlabel, ylabel, x_ticks, y_ticks):
    left, top, right, bottom = box
    draw.line((left, bottom, right, bottom), fill="#344054", width=3)
    draw.line((left, top, left, bottom), fill="#344054", width=3)
    for value, position in x_ticks:
        x = left + position * (right - left)
        draw.line((x, bottom, x, bottom + 8), fill="#344054", width=2)
        label = str(value)
        draw.text((x - draw.textlength(label, font=font(21)) / 2, bottom + 14), label, fill="#344054", font=font(21))
    for value, position in y_ticks:
        y = bottom - position * (bottom - top)
        draw.line((left - 8, y, left, y), fill="#344054", width=2)
        label = str(value)
        draw.text((left - 16 - draw.textlength(label, font=font(21)), y - 12), label, fill="#344054", font=font(21))
        draw.line((left, y, right, y), fill="#e4e7ec", width=1)
    draw.text(((left + right) / 2 - draw.textlength(xlabel, font=font(25)) / 2, bottom + 62), xlabel, fill="#172033", font=font(25))
    rotated = Image.new("RGBA", (bottom - top, 45), (255, 255, 255, 0))
    rd = ImageDraw.Draw(rotated)
    rd.text((0, 5), ylabel, fill="#172033", font=font(25))
    rotated = rotated.rotate(90, expand=True)
    return rotated


def family(name: str) -> str:
    if name in {"introsort", "quick", "quick-dual-pivot", "quick-median-three", "quick-random"}: return "pivot"
    if name.startswith("tree-"): return "tree"
    if name.startswith("merge-") or name == "tournament": return "merge"
    if "network" in name: return "network"
    return "other"


def save_trend(validation):
    image, draw = canvas("Efficiency–tail association across input sizes")
    box = (190, 170, 1680, 910)
    trend = validation["correlation_by_n"]
    xs = [math.log2(item["n"]) for item in trend]
    ys = [item["spearman"] for item in trend]
    xmin, xmax, ymin, ymax = 7, 12, 0.65, 0.85
    overlay = axes(draw, box, "Input size n (log2 scale)", "Spearman correlation", [(2**x, (x-xmin)/(xmax-xmin)) for x in range(7,13)], [(f"{y:.2f}", (y-ymin)/(ymax-ymin)) for y in (0.65,0.70,0.75,0.80,0.85)])
    image.paste(overlay, (65, box[1]), overlay)
    points=[]
    for x,y in zip(xs,ys): points.append((box[0]+(x-xmin)/(xmax-xmin)*(box[2]-box[0]), box[3]-(y-ymin)/(ymax-ymin)*(box[3]-box[1])))
    draw.line(points, fill="#1769aa", width=6)
    for (x,y),value in zip(points,ys):
        draw.ellipse((x-10,y-10,x+10,y+10), fill="#1769aa")
        draw.text((x-28,y-46), f"{value:.3f}", fill="#172033", font=font(20))
    image.save(OUTPUT / "correlation-by-size.png", dpi=(180,180))


def save_scatter(rows, validation):
    image, draw = canvas("Combined resource efficiency and power-law preference at n = 4096")
    box=(240,170,1660,920)
    tail={x['algorithm']:x for x in validation['tail_validation']}
    data=[(r['algorithm'],float(r['combined_efficiency_equal_weights_mean']),tail[r['algorithm']]['power_vs_exponential_llr_per_observation']) for r in rows if int(r['n'])==4096]
    xmax=max(x for _,x,_ in data)*1.08; ymin=-.06; ymax=.49
    overlay=axes(draw,box,"Combined efficiency η (higher is better)","PL–Exp mean log-likelihood difference",[(f"{x:.2f}",x/xmax) for x in (0,.05,.10,.15,.20,.25)],[("0.0" if y == 0 else f"{y:.1f}",(y-ymin)/(ymax-ymin)) for y in (0,.1,.2,.3,.4)])
    image.paste(overlay,(65,box[1]),overlay)
    abbreviations={"binary-insertion":"Binary ins.","bitonic-network":"Bitonic","bubble":"Bubble","heap":"Heap","insertion":"Insertion","introsort":"Intro","merge-bottom-up":"Merge BU","merge-insertion":"Merge ins.","merge-top-down":"Merge TD","odd-even-merge-network":"Odd-even","quick":"Quick","quick-dual-pivot":"Quick dual","quick-median-three":"Quick median","quick-random":"Quick deterministic","selection":"Selection","shell":"Shell","tournament":"Tournament","tree-avl":"AVL tree","tree-unbalanced":"BST"}
    labelled={"binary-insertion","bitonic-network","merge-top-down","quick","quick-dual-pivot","quick-median-three","quick-random","introsort","tree-avl","tree-unbalanced"}
    occupied=[]
    for name,x,y in sorted(data,key=lambda item:item[2],reverse=True):
        px=box[0]+x/xmax*(box[2]-box[0]); py=box[3]-(y-ymin)/(ymax-ymin)*(box[3]-box[1]); color=COLORS[family(name)]
        draw.ellipse((px-9,py-9,px+9,py+9),fill=color,outline="white",width=2)
        if name not in labelled:
            continue
        ly=py-13
        while any(abs(px-ox)<130 and abs(ly-oy)<25 for ox,oy in occupied): ly+=27
        occupied.append((px,ly)); draw.text((px+12,ly-10),abbreviations[name],fill=color,font=font(18,True))
    rho=validation['primary']['spearman']
    legend_x, legend_y = 1230, 650
    family_labels = [("pivot", "Pivot"), ("tree", "Tree"), ("merge", "Merge/tournament"), ("network", "Sorting network"), ("other", "Other")]
    for index, (group, label) in enumerate(family_labels):
        y = legend_y + 42 * index
        draw.ellipse((legend_x, y, legend_x + 18, y + 18), fill=COLORS[group])
        draw.text((legend_x + 30, y - 5), label, fill="#344054", font=font(20, True))
    draw.text((560,1040),f"Spearman rs = {rho:.3f}; 19 algorithm means",fill="#344054",font=font(24))
    image.save(OUTPUT / "efficiency-llr-scatter.png",dpi=(180,180))


def save_heatmap(validation):
    image,draw=canvas("Sensitivity to movement and storage weights")
    cells=validation['resource_weight_sensitivity']['full']['cells']; lookup={(x['movement_weight'],x['storage_weight']):x['spearman'] for x in cells}
    left,top,size=390,180,105; values=[0,.1,.25,.5,1,2,4]
    for yi,b in enumerate(reversed(values)):
        for xi,a in enumerate(values):
            v=lookup[(a,b)]; t=(v-.4)/.52; t=max(0,min(1,t)); color=(round(245-190*t),round(248-100*t),round(250-35*t))
            x=left+xi*size;y=top+yi*size;draw.rectangle((x,y,x+size,y+size),fill=color,outline="white",width=3)
            draw.text((x+size/2-draw.textlength(f"{v:.2f}",font=font(22,True))/2,y+37),f"{v:.2f}",fill="white" if t>.5 else "#172033",font=font(22,True))
    for i,a in enumerate(values): draw.text((left+i*size+size/2-draw.textlength(str(a),font=font(22))/2,top+7*size+15),str(a),fill="#344054",font=font(22))
    for i,b in enumerate(reversed(values)): draw.text((left-55,top+i*size+38),str(b),fill="#344054",font=font(22))
    draw.text((left+170,top+7*size+65),"Movement weight a",fill="#172033",font=font(26))
    draw.text((55,top+330),"Storage weight b",fill="#172033",font=font(26))
    s=validation['resource_weight_sensitivity']['full']; draw.text((1190,250),f"Range: {s['minimum']:.3f}–{s['maximum']:.3f}\nMedian: {s['median']:.3f}\nGrid cells ≥ 0.6: {100*s['fraction_at_least_0_6']:.1f}%",fill="#172033",font=font(30),spacing=18)
    image.save(OUTPUT / "weight-sensitivity.png",dpi=(180,180))


def save_ccdf(rows):
    image,draw=canvas("Representative sorting comparison network degree tails")
    box=(220,170,1650,920); names=["quick","tree-avl","merge-bottom-up","shell","bitonic-network"]; labels={"quick":"Quicksort","tree-avl":"AVL tree","merge-bottom-up":"Bottom-up merge","shell":"Shell","bitonic-network":"Bitonic network"}; colors=["#1769aa","#2e7d32","#8e24aa","#546e7a","#ef6c00"]
    selected={r['algorithm']:r for r in rows if int(r['n'])==4096 and r['algorithm'] in names}; all_points={}; xmin=math.inf;xmax=0
    for name in names:
        h={int(k):int(v) for k,v in json.loads(selected[name]['aggregate_degree_histogram']).items()}; total=sum(h.values());remaining=total;pts=[]
        for degree,count in sorted(h.items()):
            if degree>0: pts.append((degree,remaining/total))
            remaining-=count
        all_points[name]=pts;xmin=min(xmin,pts[0][0]);xmax=max(xmax,pts[-1][0])
    lx0,lx1=math.log10(xmin),math.log10(xmax);ly0,ly1=-6,0
    overlay=axes(draw,box,"Total degree k (log10 scale)","Pr(K >= k) (log10 scale)",[(f"10^{x}",(x-lx0)/(lx1-lx0)) for x in range(math.ceil(lx0),math.floor(lx1)+1)],[(f"10^{y}",(y-ly0)/(ly1-ly0)) for y in range(-6,1)])
    image.paste(overlay,(65,box[1]),overlay)
    for name,color in zip(names,colors):
        pts=[(box[0]+(math.log10(x)-lx0)/(lx1-lx0)*(box[2]-box[0]),box[3]-(math.log10(max(y,1e-6))-ly0)/(ly1-ly0)*(box[3]-box[1])) for x,y in all_points[name] if y>=1e-6]
        draw.line(pts,fill=color,width=5)
    for i,(name,color) in enumerate(zip(names,colors)):
        y=185+i*40;draw.line((1180,y,1240,y),fill=color,width=6);draw.text((1255,y-14),labels[name],fill=color,font=font(23,True))
    image.save(OUTPUT / "representative-ccdfs.png",dpi=(180,180))


def main():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    rows=list(csv.DictReader(SUMMARY.open(encoding='utf-8'))); validation=json.loads(VALIDATION.read_text())
    save_trend(validation);save_scatter(rows,validation);save_heatmap(validation);save_ccdf(rows)
    print(f"wrote four figures to {OUTPUT}")


if __name__ == '__main__': main()
