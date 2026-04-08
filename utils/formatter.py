import pandas as pd
import numpy as np

def indian_rupee(n):
    if pd.isna(n): return ""
    n = int(n)
    s = str(abs(n))
    if len(s) <= 3:
        result = s
    else:
        result = s[-3:]
        s = s[:-3]
        while s:
            result = s[-2:] + "," + result
            s = s[:-2]
    sign = "-" if n < 0 else ""
    return f"{sign}₹{result}"
