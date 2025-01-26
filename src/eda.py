import pandas as pd
import numpy as np
# from sklearn.metrics import roc_auc_score
from scipy.stats import skew
from scipy.stats import kurtosis
import matplotlib.pyplot as plt

from src import constants as c

def _get_r2_coefficient(y, discrete_predictor):
    df = pd.DataFrame({"y": y, "discrete_predictor": discrete_predictor})
    df_agg = df.groupby("discrete_predictor").agg(y_hat = ("y", "mean")).reset_index()
    y_hat = df.merge(df_agg, on="discrete_predictor")["y_hat"]
    var_y = np.var(y)
    var_e = np.var(y - y_hat)
    r2 = 1 - (var_e/var_y)
    return r2

def _compute_r2_confidence_interval(y, discrete_predictor, n_resamples, confidence_level):
    rnd = np.random.RandomState(c.seed)
    n_sample = len(y)
    significance = 1 - confidence_level
    p, q = significance/2, 1 - (significance/2)

    bootstraped_r2s = []
    
    for i in range(n_resamples): 
        index_bootstrap = rnd.choice(n_sample, n_sample)
        y_bootstrap = y[index_bootstrap]
        predictor_bootstrap = discrete_predictor[index_bootstrap]
        r2 = _get_r2_coefficient(y_bootstrap, predictor_bootstrap)
        bootstraped_r2s.append(r2)

    ci_lower, ci_upper = np.quantile(bootstraped_r2s, [p, q])

    return ci_lower, ci_upper

def _mean_target(df, categorical_feature):
    mean_target_by_level = df.groupby(categorical_feature)\
    .agg(
        mean_target = (
            c.target, "mean"
        ),
        count = (
            c.target, len
        )
    ).sort_values("mean_target")
    return mean_target_by_level

def _compute_hhi(mean_target_by_level):
    number_categories = len(mean_target_by_level)
    total_count = sum(mean_target_by_level["count"])
    hhi = mean_target_by_level["count"] / total_count
    hhi = (sum(hhi ** 2) - (1/number_categories))/(1 - (1/number_categories))
    return hhi, number_categories

def _get_most_and_least(series):
    idx_max = series.argmax()
    idx_min = series.argmin()
    levels = series.index
    return levels[idx_max], levels[idx_min]

def print_stats_for_categorical_feature(df, categorical_feature):

    mean_target_by_level = _mean_target(df, categorical_feature)
    hhi, number_categories = _compute_hhi(mean_target_by_level)
    
    most_common_level, _ = _get_most_and_least(mean_target_by_level["count"])
    highest_prop_cat, lowest_prop_cat = _get_most_and_least(mean_target_by_level["mean_target"])	
        
    df_ = df[[categorical_feature, c.target]].copy().set_index(categorical_feature)
    df_ = df_.join(mean_target_by_level, how="left")
    predictor = df_["mean_target"].values
    y = (df[c.target]).values
    
    r2 = _get_r2_coefficient(y, predictor)
    ci_lower, ci_upper = _compute_r2_confidence_interval(y, predictor, n_resamples=999, confidence_level=0.99)
    
    print("="*120)
    print(f"Summary of {categorical_feature}")
    print("="*120)
    
    print(f"Number of categories: {number_categories}")
    print(f"Most common category: {most_common_level}")
    print(f"Highest proportion of positives: {highest_prop_cat}")
    print(f"Lowest proportion of positives: {lowest_prop_cat}")
    print(f"Herfindahl–Hirschman index: {hhi * 100 :.2f}%")
    print(f"R2: {r2 * 100 :.2f}%")
    print(f"R2 confidence interval: ({ci_lower * 100 :.2f}%, {ci_upper * 100 :.2f}%)")
    display(mean_target_by_level)

def stats_for_numerical_features(df, numerical_feature):
    predictor = df[numerical_feature].values
    y = (df[c.target]).values
    
    # mean and median
    mean_pred = predictor.mean()
    median_pred = np.median(predictor)
    
    # standard deviation and range
    std_pred = predictor.std()
    range_pred = np.max(predictor) - np.min(predictor)
    
    # skewness and kurtosis
    skew_pred = skew(predictor, bias=True)
    kurt_pred = kurtosis(predictor, bias=True)
    
    # r2 and confidence interval
    deciles = np.quantile(predictor, [i/10 for i in range(1,10)], method="inverted_cdf")
    discrete_predictor = np.digitize(predictor, deciles, right=True)

    r2 = _get_r2_coefficient(y, discrete_predictor)
    ci_lower, ci_upper = _compute_r2_confidence_interval(y, discrete_predictor, n_resamples=999, confidence_level=0.99)
    
    print("="*120)
    print(f"Summary of {numerical_feature}")
    print("="*120)
    
    print(f"Mean: {mean_pred :.2f}")
    print(f"Median: {median_pred :.2f}")
    print(f"Standard Deviation: {std_pred :.2f}")
    print(f"Range: {range_pred :.2f}")
    print(f"Skewness: {skew_pred :.2f}")
    print(f"Kurtosis: {kurt_pred :.2f}")
    print(f"R2 coefficient: {r2 * 100 :.2f}%")
    print(f"R2 confidence interval: ({ci_lower * 100 :.2f}%, {ci_upper * 100 :.2f}%)")
    
    # Histogram
    fig, ax = plt.subplots()
    ax.hist(predictor, bins="doane")
    ax.set(title=f"Histogram", xlabel=numerical_feature, ylabel="Frequency")
    plt.show()