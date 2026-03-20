import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

class FrequencyEncoder(BaseEstimator, TransformerMixin):
    def __init__(self, normalize=True, handle_unknown="min"):
        self.normalize = normalize
        self.handle_unknown = handle_unknown
        self.maps_ = {}
        self.feature_names_in_ = None
        self._min_vals_ = {}

    def fit(self, X, y=None):
        X = self._to_frame(X)
        self.feature_names_in_ = list(X.columns)
        n = len(X)

        for c in self.feature_names_in_:
            vc = X[c].astype("object").fillna("__MISSING__").value_counts(dropna=False)
            if self.normalize:
                vc = vc / n
            self.maps_[c] = vc.to_dict()
            self._min_vals_[c] = min(self.maps_[c].values()) if len(self.maps_[c]) else 0.0
        return self

    def transform(self, X):
        X = self._to_frame(X, self.feature_names_in_)
        out = np.zeros((len(X), len(self.feature_names_in_)), dtype=float)

        for j, c in enumerate(self.feature_names_in_):
            s = X[c].astype("object").fillna("__MISSING__")
            m = self.maps_[c]
            if self.handle_unknown == "zero":
                out[:, j] = s.map(m).fillna(0.0).to_numpy()
            else:
                out[:, j] = s.map(m).fillna(self._min_vals_[c]).to_numpy()
        return out

    def get_feature_names_out(self, input_features=None):
        if input_features is None:
            input_features = self.feature_names_in_
        return np.array([f"{c}__freq" for c in input_features], dtype=object)

    @staticmethod
    def _to_frame(X, cols=None):
        if isinstance(X, pd.DataFrame):
            return X if cols is None else X[cols]
        if cols is None:
            cols = [f"x{i}" for i in range(X.shape[1])]
        return pd.DataFrame(X, columns=cols)


class TargetEncoder(BaseEstimator, TransformerMixin):
    def __init__(self, smoothing=10.0, handle_unknown="global"):
        self.smoothing = smoothing
        self.handle_unknown = handle_unknown
        self.maps_ = {}
        self.global_mean_ = None
        self.feature_names_in_ = None

    def fit(self, X, y):
        if y is None:
            raise ValueError("TargetEncoder requires y (supervised).")
        y = np.asarray(y).astype(float)
        X = self._to_frame(X)
        self.feature_names_in_ = list(X.columns)
        self.global_mean_ = float(np.mean(y))

        df = X.copy()
        df["_y_"] = y

        for c in self.feature_names_in_:
            g = df[[c, "_y_"]].copy()
            g[c] = g[c].astype("object").fillna("__MISSING__")
            stats = g.groupby(c)["_y_"].agg(["mean", "count"])

            k = self.smoothing
            enc = (stats["count"] * stats["mean"] + k * self.global_mean_) / (stats["count"] + k)
            self.maps_[c] = enc.to_dict()

        return self

    def transform(self, X):
        X = self._to_frame(X, self.feature_names_in_)
        out = np.zeros((len(X), len(self.feature_names_in_)), dtype=float)

        for j, c in enumerate(self.feature_names_in_):
            s = X[c].astype("object").fillna("__MISSING__")
            m = self.maps_[c]
            if self.handle_unknown == "zero":
                out[:, j] = s.map(m).fillna(0.0).to_numpy()
            else:
                out[:, j] = s.map(m).fillna(self.global_mean_).to_numpy()
        return out

    def get_feature_names_out(self, input_features=None):
        if input_features is None:
            input_features = self.feature_names_in_
        return np.array([f"{c}__target_mean" for c in input_features], dtype=object)

    @staticmethod
    def _to_frame(X, cols=None):
        if isinstance(X, pd.DataFrame):
            return X if cols is None else X[cols]
        if cols is None:
            cols = [f"x{i}" for i in range(X.shape[1])]
        return pd.DataFrame(X, columns=cols)