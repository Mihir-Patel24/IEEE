
import pandas as pd, numpy as np
mill = pd.read_csv(r'd:\IEEE\mill.csv', index_col=0)
print('Shape:', mill.shape)
print('\nPer-case info:')
for c in sorted(mill['case'].unique()):
    d = mill[mill['case']==c].sort_values('run')
    vb = d['VB'].dropna()
    max_vb = round(float(vb.max()), 3) if len(vb) > 0 else 'N/A'
    print(f"  Case {c:2d}: runs={len(d)}, VB_max={max_vb}, time_max={int(d['time'].max())}, mat={int(d['material'].iloc[0])}, DOC={d['DOC'].iloc[0]}, feed={d['feed'].iloc[0]}")

print('\nColumn dtypes:')
print(mill.dtypes)
print('\nMissing:')
print(mill.isnull().sum())
