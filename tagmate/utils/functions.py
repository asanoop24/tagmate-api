from io import StringIO
import pandas as pd


def bytes_to_df(bytes_data: bytes):
    s = str(bytes_data, "utf-8")
    data = StringIO(s)
    df = pd.read_csv(data).reset_index()
    return df