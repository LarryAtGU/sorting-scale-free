#!/usr/bin/env python3
"""Run the frozen major-revision analyses that require no new sorting executions."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path

from scn_sorting.analysis.powerlaw import _hurwitz_zeta
from scn_sorting.analysis.tail_validation import (
    fit_alternative_tails,
    fit_finite_power_law,
    fit_power_law_tail_vectorized,
)

WEIGHTS = [0, 0.1, 0.25, 0.5, 1, 2, 4]
TAIL_FRACTIONS = [0.05, 0.10, 0.20, 0.30]
FAMILIES = {
    "pivot": ["introsort", "quick", "quick-dual-pivot", "quick-median-three", "quick-random"],
    "tree": ["tree-avl", "tree-unbalanced"],
    "merge": ["merge-bottom-up", "merge-top-down", "merge-insertion"],
    "network": ["bitonic-network", "odd-even-merge-network"],
    "insertion": ["insertion", "binary-insertion"],
    "tournament": ["tournament"], "heap": ["heap"], "shell": ["shell"],
    "exchange": ["bubble"], "selection": ["selection"],
}
FAMILY_BY_ALGORITHM = {algorithm: family for family, algorithms in FAMILIES.items() for algorithm in algorithms}


def ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__); result = [0.0] * len(values); i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]: j += 1
        rank = (i + j - 1) / 2 + 1
        for position in order[i:j]: result[position] = rank
        i = j
    return result


def spearman(left: list[float], right: list[float]) -> float:
    x, y = ranks(left), ranks(right); xm, ym = statistics.fmean(x), statistics.fmean(y)
    numerator = sum((a-xm)*(b-ym) for a,b in zip(x,y)); denominator = math.sqrt(sum((a-xm)**2 for a in x)*sum((b-ym)**2 for b in y))
    return numerator / denominator if denominator else math.nan


def percentile(values: list[float], p: float) -> float:
    ordered = sorted(values); position = (len(ordered)-1)*p; low = int(position); part = position-low
    return ordered[low] if low+1 == len(ordered) else ordered[low]*(1-part)+ordered[low+1]*part


def histogram(row: dict[str, str]) -> dict[int, int]:
    return {int(key): int(value) for key, value in json.loads(row["aggregate_degree_histogram"]).items()}


def fixed_tail_fit(values: dict[int, int], requested_fraction: float) -> dict[str, float | int]:
    total = sum(values.values()); target = math.ceil(total * requested_fraction); accumulated = 0; xmin = 0
    for degree in sorted(values, reverse=True):
        accumulated += values[degree]; xmin = degree
        if accumulated >= target: break
    tail = [(degree, count) for degree, count in sorted(values.items()) if degree >= xmin]
    count = sum(frequency for _, frequency in tail)
    denominator = sum(frequency * math.log(degree / (xmin - 0.5)) for degree, frequency in tail)
    alpha = 1 + count / denominator
    power_ll = sum(frequency * (-alpha*math.log(degree)-math.log(_hurwitz_zeta(alpha,xmin))) for degree,frequency in tail)
    mean_offset = sum((degree-xmin)*frequency for degree,frequency in tail)/count
    if mean_offset:
        q = mean_offset/(mean_offset+1)
        exp_ll = sum(frequency*(math.log1p(-q)+(degree-xmin)*math.log(q)) for degree,frequency in tail)
        total_llr = power_ll-exp_ll
    else: total_llr = -math.inf
    return {"requested_fraction": requested_fraction, "actual_fraction": count/total, "xmin": xmin, "alpha": alpha, "tail_count": count, "total_llr": total_llr, "mean_llr": total_llr/count}


def summarize(values: list[float]) -> dict[str, float]:
    return {"minimum": min(values), "q25": percentile(values,.25), "median": statistics.median(values), "q75": percentile(values,.75), "maximum": max(values)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, default=Path("data/results/batch-paper-final-19-algorithms-summary.csv"))
    parser.add_argument("--runs", type=Path, default=Path("data/results/batch-paper-final-19-algorithms-runs.jsonl.gz"))
    parser.add_argument("--output", type=Path, default=Path("data/results/paper-major-revision-analysis.json"))
    args = parser.parse_args()
    rows = list(csv.DictReader(args.summary.open(encoding="utf-8")))
    fitted = {}
    finite_size = []
    for row in rows:
        fit = fit_power_law_tail_vectorized(histogram(row)); fitted[(row["algorithm"],int(row["n"]))] = fit
        finite_size.append({"algorithm":row["algorithm"],"family":FAMILY_BY_ALGORITHM[row["algorithm"]],"n":int(row["n"]),"alpha":fit.alpha,"xmin":fit.xmin,"xmin_fraction":fit.xmin/int(row["n"]),"tail_fraction":fit.tail_fraction,"tail_span_decades":fit.tail_span_decades,"maximum_degree":float(row["maximum_degree_mean"]),"maximum_degree_fraction":float(row["maximum_degree_mean"])/int(row["n"])})

    decomposition_by_n = []
    definitions = {"c":"c", "w":"w", "s":"s", "c+w":"c+w", "c+s":"c+s", "w+s":"w+s", "c+w+s":"c+w+s"}
    for n in sorted({int(row["n"]) for row in rows}):
        selected = [row for row in rows if int(row["n"])==n]; outcomes=[fitted[(row["algorithm"],n)].power_vs_exponential_llr_per_observation for row in selected]
        resources=[]
        for row in selected: resources.append({"c":float(row["normalized_excess_comparisons_mean"]),"w":float(row["movements_per_node_mean"]),"s":float(row["peak_auxiliary_storage_fraction_mean"])})
        correlations={}
        for label,expression in definitions.items():
            terms=expression.split("+"); eta=[1/(1+sum(resource[term] for term in terms)) for resource in resources]
            correlations[label]=spearman(eta,outcomes)
        decomposition_by_n.append({"n":n,"correlations":correlations})

    primary_rows=[row for row in rows if int(row["n"])==4096]
    outcome=[fitted[(row["algorithm"],4096)].power_vs_exponential_llr_per_observation for row in primary_rows]
    resource_records=[]
    for row in primary_rows:
        c=float(row["normalized_excess_comparisons_mean"]);w=float(row["movements_per_node_mean"]);s=float(row["peak_auxiliary_storage_fraction_mean"]);q=c+w+s
        resource_records.append({"algorithm":row["algorithm"],"c":c,"w":w,"s":s,"c_share":c/q,"w_share":w/q,"s_share":s/q})
    resource_ranges={key:summarize([record[key] for record in resource_records]) for key in ("c","w","s","c_share","w_share","s_share")}

    grids={}
    for transform in ("raw","log"):
        cells=[]
        for a in WEIGHTS:
            for b in WEIGHTS:
                eta=[]
                for record in resource_records:
                    w = record["w"] if transform=="raw" else math.log1p(record["w"])
                    s = record["s"] if transform=="raw" else math.log1p(record["s"])
                    eta.append(1/(1+record["c"]+a*w+b*s))
                cells.append({"movement_weight":a,"storage_weight":b,"spearman":spearman(eta,outcome)})
        grids[transform]={"cells":cells,**summarize([cell["spearman"] for cell in cells]),"fraction_at_least_0_6":sum(cell["spearman"]>=.6 for cell in cells)/len(cells)}

    algorithms=[row["algorithm"] for row in primary_rows]; efficiency=[float(row["combined_efficiency_equal_weights_mean"]) for row in primary_rows]
    def selected_correlation(excluded:set[str]) -> float:
        indices=[i for i,name in enumerate(algorithms) if FAMILY_BY_ALGORITHM[name] not in excluded]
        return spearman([efficiency[i] for i in indices],[outcome[i] for i in indices])
    family_means=[]
    for family,members in FAMILIES.items():
        indices=[algorithms.index(name) for name in members]
        family_means.append({"family":family,"algorithm_count":len(indices),"efficiency":statistics.fmean(efficiency[i] for i in indices),"llr":statistics.fmean(outcome[i] for i in indices)})
    family_rho=spearman([x["efficiency"] for x in family_means],[x["llr"] for x in family_means])
    rng=random.Random("scn-family-cluster-bootstrap-v1"); boot=[]; failed=0
    for _ in range(10000):
        chosen=[rng.choice(list(FAMILIES)) for _ in FAMILIES]; bx=[];by=[]
        for family in chosen:
            for name in FAMILIES[family]:
                i=algorithms.index(name);bx.append(efficiency[i]);by.append(outcome[i])
        value=spearman(bx,by)
        if math.isfinite(value):boot.append(value)
        else:failed+=1
    family_analysis={"full":selected_correlation(set()),"pivot_excluded":selected_correlation({"pivot"}),"tree_excluded":selected_correlation({"tree"}),"pivot_and_tree_excluded":selected_correlation({"pivot","tree"}),"family_means":family_means,"family_mean_spearman":family_rho,"cluster_bootstrap_replicates":10000,"cluster_bootstrap_failed":failed,"cluster_bootstrap_95_percentile_interval":[percentile(boot,.025),percentile(boot,.975)]}

    fixed=[]
    for row in primary_rows:
        for fraction in TAIL_FRACTIONS: fixed.append({"algorithm":row["algorithm"],**fixed_tail_fit(histogram(row),fraction)})

    blocks=defaultdict(lambda:{"histogram":defaultdict(int),"efficiency":[]})
    with gzip.open(args.runs,"rt",encoding="utf-8") as stream:
        for line_number,line in enumerate(stream,1):
            record=json.loads(line)
            if record["n"] != 4096: continue
            block=(record["seed"]-1)//50
            target=blocks[(record["algorithm"],block)]
            for degree,count in record["degree_histogram"].items(): target["histogram"][int(degree)]+=int(count)
            target["efficiency"].append(float(record["combined_efficiency_equal_weights"]))
            if line_number % 20000 == 0: print(f"read {line_number} run records",flush=True)
    if len(blocks)!=19*20 or any(len(value["efficiency"])!=50 for value in blocks.values()): raise ValueError("incomplete 20-by-50 block design")
    block_rows=[]
    for (algorithm,block),value in sorted(blocks.items()):
        block_histogram=dict(value["histogram"]);fit=fit_power_law_tail_vectorized(block_histogram)
        alternatives=fit_alternative_tails(block_histogram,fit.xmin,fit.alpha)
        finite=fit_finite_power_law(block_histogram,fit.xmin,4095)
        block_rows.append({"algorithm":algorithm,"family":FAMILY_BY_ALGORITHM[algorithm],"block":block+1,"first_seed":block*50+1,"last_seed":block*50+50,"efficiency":statistics.fmean(value["efficiency"]),"alpha":fit.alpha,"xmin":fit.xmin,"tail_fraction":fit.tail_fraction,"tail_span_decades":fit.tail_span_decades,"ks":fit.ks_distance,"llr":fit.power_vs_exponential_llr_per_observation,"power_vs_lognormal_llr":alternatives.power_vs_lognormal_llr_per_observation,"power_vs_stretched_exponential_llr":alternatives.power_vs_stretched_exponential_llr_per_observation,**finite.as_dict()})
    block_correlations=[]
    for block in range(1,21):
        selected=[row for row in block_rows if row["block"]==block]
        block_correlations.append({"block":block,"first_seed":selected[0]["first_seed"],"last_seed":selected[0]["last_seed"],"spearman":spearman([row["efficiency"] for row in selected],[row["llr"] for row in selected])})
    block_summaries=[]
    for algorithm in algorithms:
        selected=[row for row in block_rows if row["algorithm"]==algorithm]
        block_summaries.append({"algorithm":algorithm,**{metric:summarize([float(row[metric]) for row in selected]) for metric in ("alpha","xmin","tail_fraction","tail_span_decades","ks","llr","power_vs_lognormal_llr","power_vs_stretched_exponential_llr","finite_vs_unbounded_power_llr_per_observation","finite_power_vs_exponential_llr_per_observation")}})

    document={"schema_version":1,"protocol":"docs/major-revision-analysis-protocol.md","resource_decomposition_by_n":decomposition_by_n,"resource_records_n4096":resource_records,"resource_ranges_n4096":resource_ranges,"weight_grids_n4096":grids,"family_analysis_n4096":family_analysis,"fixed_tail_sensitivity_n4096":fixed,"finite_size_diagnostics":finite_size,"block_design":{"blocks":20,"executions_per_block":50,"rows":block_rows,"correlations":block_correlations,"correlation_summary":summarize([row["spearman"] for row in block_correlations]),"algorithm_summaries":block_summaries}}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(document,indent=2)+"\n",encoding="utf-8");print(f"wrote {args.output}")


if __name__=="__main__": main()
