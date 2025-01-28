import pandas as pd
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
import scipy.stats as sps

dist = sps.norm()

def _combine_mean(mean_x, mean_y, n, m):
    p = n/(n+m)
    mean_z = p*mean_x + (1-p)*mean_y
    return mean_z

def _combine_variance(mean_x, mean_y, variance_x, variance_y, n, m):
    term_x = (n - 1) * variance_x
    term_y = (m - 1) * variance_y
    difference_term = (n * m / (n + m)) * (mean_x - mean_y)**2
    variance_z = (term_x + term_y + difference_term) / (n + m - 1)
    return variance_z

def _combine_population(mean_x, mean_y, variance_x, variance_y, n, m):
    mean_z = _combine_mean(mean_x, mean_y, n, m)
    variance_z = _combine_variance(mean_x, mean_y, variance_x, variance_y, n, m)
    obs = n + m
    return mean_z, variance_z, obs

#######################
def unbiased_var(y):
    return np.var(y, ddof=1)

def init_table(x, y):
    table = pd.DataFrame({"x": x, "y": y})
    stats = {"mean_y": ("y", "mean"), "variance_y": ("y", unbiased_var), "n": ("y", len)}
    table = table.groupby("x").agg(**stats)
    index = table.index.tolist()
    index = [(idx,) for idx in index]
    table.index = index
    # si el número de observaciones es uno, var = nan, en este caso asignamos 
    # la varianza global
    table.loc[table["n"]==1, "variance_y"] = unbiased_var(y) 
    return table

def confidence_interval(mean_y, variance_y, n):
    "calcula intervalo de confianza normal del 99%"
    alpha = 0.01
    z = sps.norm().ppf(1 - 0.5*alpha)
    deviation = z * np.sqrt(variance_y) / np.sqrt(n)
    return mean_y - deviation, mean_y + deviation

def _there_is_intersection(ci_i, ci_j):
    x_i, y_i = ci_i
    x_j, y_j = ci_j
    return np.minimum(y_i, y_j) - np.maximum(x_i, x_j) > 0

def there_is_intersection(table, i, j):
    """Constructs the confidence intervarls for categories i and j"""
    mean_y_i, variance_y_i, n_i = table.iloc[i]
    mean_y_j, variance_y_j, n_j = table.iloc[j]

    ci_i = confidence_interval(mean_y_i, variance_y_i, n_i)
    ci_j = confidence_interval(mean_y_j, variance_y_j, n_j)

    return _there_is_intersection(ci_i, ci_j)

def merge_categories(table, i, j):
    """Removes category j and add it to i"""
    index = table.index.tolist()
    category_i = index[i]
    category_j = index[j]

    # unimos las dos categorias aqui
    mean_y_i, variance_y_i, n_i = table.iloc[i]
    mean_y_j, variance_y_j, n_j = table.iloc[j]
    
    table.iloc[i] = _combine_population(mean_y_i, mean_y_j, mean_y_i, variance_y_j, n_i, n_j)
    
    table = table.drop(category_j, axis=0)
    index[i] = index[i] + index[j]
    index.pop(j)

    table.index = index
    return table

def merge_similar_categories(x, y):
    # inicializamos la tabla
    # tabla: categorias (index), mean_y, variance_y, n. obs.
    table = init_table(x, y)
    n = len(table)
    i = 0
    while i < n:
        j = i + 1
        while j < n:
            if there_is_intersection(table, i, j):
                table = merge_categories(table, i, j)
                n -= 1
            else:
                j += 1
        i += 1
    table = table.sort_values("mean_y")
    return table

class CustomTransformer(BaseEstimator, TransformerMixin):

    def __init__(self, variables_to_eliminate, discrete_variables, continous_variables, lower_q=0.001, upper_q=0.999):
        self.variables_to_eliminate = variables_to_eliminate
        self.discrete_variables = [col for col in discrete_variables if col not in variables_to_eliminate]
        self.continous_variables = [col for col in continous_variables if col not in variables_to_eliminate]
        self.lower_q = lower_q
        self.upper_q = upper_q

    def fit(self, X, y):
        dict_merged_levesl = {}
        dict_outliers_threshold = {}
        dict_tables = {}

        for feature in self.discrete_variables:
            x = X[feature].values
            table = merge_similar_categories(x, y)
            groups = table.index.tolist()
            group_mapping = dict(zip(groups, range(len(groups))))
            dict_merged_levesl[feature] = group_mapping
            dict_tables[feature] = table

        for feature in self.continous_variables:
            x = X[feature].values
            lower_threshold, upper_threshold = np.quantile(x, [self.lower_q, self.upper_q], method="inverted_cdf")
            dict_outliers_threshold[feature] = lower_threshold, upper_threshold

        self.dict_merged_levesl = dict_merged_levesl
        self.dict_outliers_threshold = dict_outliers_threshold
        self.dict_tables = dict_tables

        return self

    def transform(self, X, y=None, training=False):
        X_transformed = X.copy()
        X_transformed = X_transformed.drop(columns=self.variables_to_eliminate)

        # grouping categories
        for feature, group_mapping in self.dict_merged_levesl.items():
            for group, value in group_mapping.items():
                X_transformed[feature] = X_transformed[feature].replace(to_replace=group, value=str(value))

        # filtering outliers only if training
        if training:
            final_mask = np.repeat(True, len(X))
            for feature, thresholds in self.dict_outliers_threshold.items():
                lower_threshold, upper_threshold = thresholds
                mask = (lower_threshold <= X_transformed[feature]) & (X_transformed[feature] <= upper_threshold)
                final_mask &= mask
            X_transformed = X_transformed[final_mask]
            self.final_mask = final_mask

        X_transformed = pd.get_dummies(X_transformed, columns=self.discrete_variables, drop_first=True).astype(float)

        return X_transformed