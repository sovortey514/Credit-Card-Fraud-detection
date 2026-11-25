from scripts.tune_xgboost_genetic import genetic_search


def test_genetic_search_is_reproducible_and_keeps_best_candidate():
    def fitness(params):
        return params["learning_rate"] + params["subsample"] - params["max_depth"] / 10
    first = genetic_search(fitness, seed=42, population_size=4, generations=3)
    second = genetic_search(fitness, seed=42, population_size=4, generations=3)
    assert first == second
    assert len(first[2]) == 12
    assert first[1] == max(item["average_precision"] for item in first[2])
    assert 2 <= first[0]["max_depth"] <= 8
