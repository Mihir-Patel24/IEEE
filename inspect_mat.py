
import scipy.io as sio
import numpy as np

mat = sio.loadmat(r'd:\IEEE\mill\mill.mat')
print("Keys:", [k for k in mat.keys() if not k.startswith('_')])

data = mat['mill']
print("\nmill shape:", data.shape)
print("mill dtype:", data.dtype)
print("dtype names (fields):", data.dtype.names)

# Show first case
case0 = data[0, 0]
print("\nCase 0 fields:")
for name in data.dtype.names:
    val = data[0, 0][name]
    print(f"  {name}: shape={np.array(val).shape}, dtype={np.array(val).dtype}")
