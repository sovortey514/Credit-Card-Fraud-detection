"""SHAP-based explanations for tree fraud models."""

from __future__ import annotations

import pandas as pd
import shap


class FraudExplainer:
    """Explain which model features increase fraud risk for a transaction."""

    def __init__(self, model):
        self.model = model
        self.explainer = shap.TreeExplainer(model)

    def explain_transaction(
        self,
        df_features: pd.DataFrame,
        top_n: int = 3,
    ) -> list[str]:
        """Return the top positive SHAP drivers for one input row."""
        if len(df_features) != 1:
            raise ValueError("explain_transaction expects exactly one input row")

        shap_values = self.explainer.shap_values(df_features)
        if hasattr(shap_values, "values"):
            shap_values = shap_values.values
        if isinstance(shap_values, list):
            vals = shap_values[1][0]
        elif len(shap_values.shape) == 3:
            vals = shap_values[0, :, 1]
        elif len(shap_values.shape) == 2:
            vals = shap_values[0]
        else:
            vals = shap_values

        contributions = pd.Series(vals, index=df_features.columns).sort_values(
            ascending=False
        )
        return [
            f"Feature '{feature}' increased risk score (impact: +{value:.4f})"
            for feature, value in contributions.head(top_n).items()
            if value > 0
        ]
