import argparse
import math
import os
import re
import sys
import warnings

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402
from statsmodels.stats.multitest import multipletests  # noqa: E402

from study.design import Clarity, Policy  # noqa: E402
from study.logger import read_jsonl  # noqa: E402

POLICIES = [p.value for p in Policy]
CLARITIES = [c.value for c in Clarity]
NEVER, WHEN, ALWAYS = (p.value for p in Policy)

POLICY_TERM = "C(policy, Treatment(reference='never_ask'))"
CLARITY_TERM = "C(clarity, Treatment(reference='vague'))"
RHS = f"{POLICY_TERM} * {CLARITY_TERM}"


# ---------- loading ----------

def frame_from_records(records: list[dict], arm: str = "human"):
    df = pd.DataFrame(records)
    if df.empty:
        return df, 0
    excluded = int(df["technical_failure"].sum())
    df = df[~df["technical_failure"]].copy()
    if "repeat" not in df:
        df["repeat"] = 0
    if arm == "simulation":
        df["unit"] = df["task_id"] + "#" + df["repeat"].fillna(0).astype(int).astype(str)
        df["cluster"] = df["task_id"]
    else:
        df["unit"] = df["participant_id"]
        df["cluster"] = df["participant_id"]
    df["log_tokens"] = np.log(df["total_tokens"].clip(lower=1))
    df["passed"] = df["passed"].astype(int)
    return df.reset_index(drop=True), excluded


def load_sessions(path: str, arm: str = "human"):
    return frame_from_records(read_jsonl(path), arm)


# ---------- descriptives ----------

def summarize(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for clarity in CLARITIES:
        for policy in POLICIES:
            cell = df[(df.clarity == clarity) & (df.policy == policy)]
            if cell.empty:
                continue
            solved = int(cell.passed.sum())
            rating = pd.to_numeric(cell["rating"], errors="coerce").mean() if "rating" in cell else float("nan")
            rows.append({
                "clarity": clarity,
                "policy": policy,
                "n": len(cell),
                "success_rate": cell.passed.mean(),
                "mean_tokens": cell.total_tokens.mean(),
                "median_tokens": cell.total_tokens.median(),
                "tokens_per_solved": cell.total_tokens.sum() / solved if solved else float("nan"),
                "mean_questions": cell.n_questions.mean(),
                "mean_prompts": cell.student_prompts.mean(),
                "mean_minutes": cell.wall_seconds.mean() / 60,
                "mean_rating": rating,
            })
    return pd.DataFrame(rows)


def bootstrap_ci(values, n_boot: int = 5000, seed: int = 1):
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    samples = rng.choice(values, size=(n_boot, len(values)), replace=True)
    low, high = np.percentile(samples.mean(axis=1), [2.5, 97.5])
    return float(low), float(high)


# ---------- paired contrasts ----------

def paired(df: pd.DataFrame, clarity: str, policy_a: str, policy_b: str):
    a = df[(df.clarity == clarity) & (df.policy == policy_a)].set_index("unit")
    b = df[(df.clarity == clarity) & (df.policy == policy_b)].set_index("unit")
    a = a[~a.index.duplicated(keep="last")]
    b = b[~b.index.duplicated(keep="last")]
    common = a.index.intersection(b.index)
    return a.loc[common], b.loc[common]


def run_contrasts(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for clarity in CLARITIES:
        for policy_a, policy_b in [(WHEN, NEVER), (ALWAYS, NEVER), (ALWAYS, WHEN)]:
            a, b = paired(df, clarity, policy_a, policy_b)
            n = len(a)
            if n < 2:
                continue
            diff = a["log_tokens"].to_numpy() - b["log_tokens"].to_numpy()
            low, high = bootstrap_ci(diff)
            try:
                p_tokens = float(stats.wilcoxon(diff).pvalue)
            except ValueError:  # all differences are zero
                p_tokens = 1.0
            spread = diff.std(ddof=1)
            success_a = a["passed"].to_numpy()
            success_b = b["passed"].to_numpy()
            only_a = int(((success_a == 1) & (success_b == 0)).sum())
            only_b = int(((success_a == 0) & (success_b == 1)).sum())
            discordant = only_a + only_b
            p_success = float(stats.binomtest(only_a, discordant, 0.5).pvalue) if discordant else 1.0
            rows.append({
                "clarity": clarity,
                "a": policy_a,
                "b": policy_b,
                "n_pairs": n,
                "token_ratio": math.exp(diff.mean()),
                "ci_low": math.exp(low),
                "ci_high": math.exp(high),
                "dz": diff.mean() / spread if spread > 0 else float("nan"),
                "p_tokens": p_tokens,
                "success_a": success_a.mean(),
                "success_b": success_b.mean(),
                "p_success": p_success,
            })
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["p_tokens_holm"] = multipletests(out["p_tokens"], method="holm")[1]
    out["p_success_holm"] = multipletests(out["p_success"], method="holm")[1]
    return out


# ---------- models ----------

def clean_term(term: str) -> str:
    return term.replace(POLICY_TERM, "policy").replace(CLARITY_TERM, "clarity")


def coef_table(params, bse, pvalues, label: str) -> str:
    rows = []
    for name in params.index:
        estimate, error = float(params[name]), float(bse[name])
        rows.append({
            "term": clean_term(name),
            label: math.exp(estimate),
            "ci_low": math.exp(estimate - 1.96 * error),
            "ci_high": math.exp(estimate + 1.96 * error),
            "p": float(pvalues[name]),
        })
    return md_table(pd.DataFrame(rows), digits=3)


def mixed_models(df: pd.DataFrame, arm: str = "human") -> dict:
    import statsmodels.api as sm
    import statsmodels.formula.api as smf

    results = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            if arm == "human":
                data = df.assign(all_rows=1)
                components = {"participant": "0 + C(participant_id)"}
                if df["task_id"].nunique() > 1:
                    components["task"] = "0 + C(task_id)"
                model = smf.mixedlm(f"log_tokens ~ {RHS}", data, groups="all_rows", vc_formula=components)
            else:
                model = smf.mixedlm(f"log_tokens ~ {RHS}", df, groups="cluster")
            fit = model.fit(reml=True)
            names = fit.fe_params.index
            table = coef_table(fit.fe_params, fit.bse_fe, fit.pvalues[names], "ratio")
            note = "" if fit.converged else "\n\nWarning: the model did not converge."
            results["tokens"] = table + note
        except Exception as e:
            results["tokens"] = f"Model failed: {type(e).__name__}: {e}"

        try:
            gee = smf.gee(f"passed ~ {RHS}", groups="cluster", data=df,
                          family=sm.families.Binomial(), cov_struct=sm.cov_struct.Exchangeable())
            fit = gee.fit()
            results["success"] = coef_table(fit.params, fit.bse, fit.pvalues, "odds_ratio")
        except Exception as e:
            results["success"] = f"Model failed: {type(e).__name__}: {e}"
    return results


# ---------- manipulation check ----------

def specificity(prompt: str, task: dict) -> float:
    """Crude proxy: the share of the task's ambiguities that the prompt seems to
    mention. Validate it by hand-coding a sample before relying on it."""
    lowered = prompt.lower()
    hits = sum(1 for item in task["ambiguities"] if any(k in lowered for k in item["keywords"]))
    return hits / len(task["ambiguities"])


def add_specificity(df: pd.DataFrame) -> pd.DataFrame:
    try:
        from study.tasks import load_task
        cache = {}
        values = []
        for _, row in df.iterrows():
            task = cache.setdefault(row["task_id"], load_task(row["task_id"]))
            values.append(specificity(row["prompts"][0], task))
        df = df.copy()
        df["first_prompt_specificity"] = values
    except Exception:
        pass
    return df


# ---------- power ----------

def required_n(sd_diff: float, ratio: float, alpha: float = 0.05 / 6, power: float = 0.8):
    delta = abs(math.log(ratio))
    if delta == 0 or not sd_diff or math.isnan(sd_diff):
        return float("nan")
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_power = stats.norm.ppf(power)
    return math.ceil(((z_alpha + z_power) * sd_diff / delta) ** 2) + 2


def power_table(df: pd.DataFrame, clarity: str = "vague", a: str = WHEN, b: str = NEVER):
    first, second = paired(df, clarity, a, b)
    if len(first) < 3:
        return None, float("nan"), len(first)
    diff = first["log_tokens"].to_numpy() - second["log_tokens"].to_numpy()
    spread = float(diff.std(ddof=1))
    rows = [{"token_ratio_to_detect": r, "participants_needed": required_n(spread, r)}
            for r in (0.9, 0.8, 0.7, 0.6)]
    return pd.DataFrame(rows), spread, len(first)


# ---------- report ----------

def md_table(frame: pd.DataFrame, digits: int = 2) -> str:
    if frame is None or frame.empty:
        return "(no data)"
    columns = list(frame.columns)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in frame.iterrows():
        cells = []
        for value in row:
            if isinstance(value, (float, np.floating)):
                cells.append("-" if math.isnan(value) else f"{value:.{digits}f}")
            else:
                cells.append(str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def build_report(df: pd.DataFrame, excluded: int, arm: str = "human", include_power: bool = True) -> str:
    lines = [f"# Results ({arm} arm)", ""]
    lines += ["## Data", "",
              f"- sessions analysed: {len(df)}",
              f"- units (participants, or task repeats in the simulation): {df['unit'].nunique()}",
              f"- sessions excluded for technical failure: {excluded}", ""]
    lines += ["## Descriptives (per cell)", "", md_table(summarize(df)), ""]
    lines += ["## Pre-specified contrasts (paired, Holm-corrected within each outcome)", "",
              "`token_ratio` below 1 means policy `a` used fewer tokens than policy `b`.", "",
              md_table(run_contrasts(df), digits=3), ""]
    models = mixed_models(df, arm)
    lines += ["## Mixed models", "",
              "### log(total tokens): ratios of geometric means", "", models["tokens"], "",
              "### Success (logistic GEE, clustered): odds ratios", "", models["success"], ""]
    if "first_prompt_specificity" in df:
        check = df.groupby("clarity")["first_prompt_specificity"].mean().reset_index()
        lines += ["## Manipulation check (crude proxy)", "",
                  "Share of a task's ambiguities mentioned in the first prompt. Hand-code a sample to validate.", "",
                  md_table(check), ""]
    if include_power:
        table, spread, n = power_table(df)
        lines += ["## Power planning", ""]
        if table is None:
            lines += ["Not enough pairs yet (need at least 3).", ""]
        else:
            lines += [f"SD of paired log-token differences (vague, ask_when_unclear vs never_ask): {spread:.3f} from {n} pairs.",
                      "Rough guide only, since pilot samples are small. Alpha is 0.05/6, power 0.8.", "",
                      md_table(table, digits=0), ""]
    lines += ["## Notes", "",
              "- Exploratory until the design is frozen and the target sample is reached.",
              "- Report null and unexpected results as well.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Analyse study sessions")
    parser.add_argument("--data", default=os.path.join("study_data", "sessions.jsonl"))
    parser.add_argument("--arm", choices=["human", "simulation"], default="human")
    parser.add_argument("--out", default=None)
    parser.add_argument("--demo", action="store_true", help="Use synthetic data to preview the report")
    args = parser.parse_args()

    if args.demo:
        from study.fake_data import fake_records
        df, excluded = frame_from_records(fake_records(), "human")
        out_dir = args.out or os.path.join("study_data", "results_demo")
        print("DEMO: synthetic data, not real results.\n")
    else:
        df, excluded = load_sessions(args.data, args.arm)
        out_dir = args.out or os.path.join("study_data", "results")

    if df.empty:
        print("No sessions found.")
        return

    df = add_specificity(df)
    report = build_report(df, excluded, "human" if args.demo else args.arm)
    print(report)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "results.md"), "w") as f:
        f.write(report)
    summarize(df).to_csv(os.path.join(out_dir, "summary.csv"), index=False)
    print(f"Saved to {out_dir}/")


if __name__ == "__main__":
    main()