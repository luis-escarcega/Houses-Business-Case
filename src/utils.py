import pickle
import pandas as pd

def save_to_pickle(obj, path):
    with open(path, 'wb') as file:
        pickle.dump(obj, file, protocol=pickle.HIGHEST_PROTOCOL)

def read_pickle(path):
    with open(path, 'rb') as file:
        obj = pickle.load(file)
    return obj

def save_information(X, y, target_name, path):
    df = X.copy()
    df[target_name] = y
    df.to_feather(path)