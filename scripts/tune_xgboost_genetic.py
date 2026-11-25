"""Chronological XGBoost baseline and seeded genetic hyperparameter search."""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score
from xgboost import XGBClassifier

from scripts.compare_feature_baselines import prepare

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed"
REPORT = ROOT / "reports/xgboost_genetic"
MODELS = ROOT / "models/xgboost_genetic"
SEED = 42


def model(parameters):
    return XGBClassifier(n_estimators=200, scale_pos_weight=578, tree_method="hist", n_jobs=4, random_state=SEED, **parameters)


def genetic_search(fitness, seed=SEED, population_size=6, generations=3):
    """Maximize fitness using elitism, tournament selection, crossover and mutation."""
    if population_size < 2 or generations < 1:
        raise ValueError("At least two candidates and one generation are required")
    rng = np.random.default_rng(seed)
    def random_candidate():
        return [float(rng.uniform(0.02, 0.3)), int(rng.integers(2, 9)), float(rng.uniform(0.6, 1.0))]
    population = [random_candidate() for _ in range(population_size)]
    log = []
    best = None
    for generation in range(generations):
        evaluated = []
        for candidate in population:
            params = {"learning_rate": candidate[0], "max_depth": int(candidate[1]), "subsample": candidate[2]}
            score = float(fitness(params))
            if not np.isfinite(score):
                raise ValueError("Fitness must be finite")
            evaluated.append((score, candidate.copy()))
            log.append({"generation": generation + 1, "parameters": params, "average_precision": score})
            print(f"generation {generation + 1}: {params} AP={score:.6f}", flush=True)
        evaluated.sort(key=lambda pair: pair[0], reverse=True)
        if best is None or evaluated[0][0] > best[0]:
            best = evaluated[0]
        next_population = [evaluated[0][1].copy()]
        while len(next_population) < population_size:
            def select():
                indices = rng.integers(0, len(evaluated), size=2)
                return max((evaluated[i] for i in indices), key=lambda pair: pair[0])[1]
            left, right = select(), select()
            child = [left[i] if rng.random() < 0.5 else right[i] for i in range(3)]
            replacement = random_candidate()
            for i in range(3):
                if rng.random() < 0.3:
                    child[i] = replacement[i]
            next_population.append(child)
        population = next_population
    return {"learning_rate": best[1][0], "max_depth": int(best[1][1]), "subsample": best[1][2]}, best[0], log


def main():
    train = pd.read_parquet(DATA / "creditcard_train.parquet").reset_index(drop=True)
    validation = pd.read_parquet(DATA / "creditcard_validation.parquet").reset_index(drop=True)
    # Keep equal timestamps in the same partition.
    cutoff = train["Time"].iloc[int(len(train) * 0.8)]
    inner_train = train[train["Time"] < cutoff]
    inner_validation = train[train["Time"] >= cutoff]
    _, inner_x, inner_v = prepare(inner_train, inner_validation, "F1")
    def fitness(parameters):
        candidate = model(parameters).fit(inner_x, inner_train["Class"])
        return average_precision_score(inner_validation["Class"], candidate.predict_proba(inner_v)[:, 1])
    best, best_ap, history = genetic_search(fitness)
    preprocessor, x_train, x_validation = prepare(train, validation, "F1")
    REPORT.mkdir(parents=True, exist_ok=True)
    MODELS.mkdir(parents=True, exist_ok=True)
    result = {"seed": SEED, "feature_set": "F1", "scale_pos_weight": 578, "trees": 200,
              "fitness": "inner chronological validation average precision (PR-AUC)",
              "inner_train_rows": len(inner_train), "inner_validation_rows": len(inner_validation),
              "outer_validation_rows": len(validation), "test_used": False,
              "population_size": 6, "generations": 3, "best_parameters": best,
              "best_inner_average_precision": best_ap, "search_history": history, "models": {}}
    for name, params in (("baseline", {"learning_rate": 0.3, "max_depth": 6, "subsample": 1.0}), ("genetic", best)):
        trained = model(params).fit(x_train, train["Class"])
        probabilities = trained.predict_proba(x_validation)[:, 1]
        result["models"][name] = {"parameters": params, "validation_average_precision": float(average_precision_score(validation["Class"], probabilities)), "validation_roc_auc": float(roc_auc_score(validation["Class"], probabilities))}
        joblib.dump({"model": trained, "preprocessor": preprocessor, "feature_set": "F1"}, MODELS / f"{name}.joblib")
    (REPORT / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result["models"], indent=2), flush=True)


if __name__ == "__main__":
    main()
