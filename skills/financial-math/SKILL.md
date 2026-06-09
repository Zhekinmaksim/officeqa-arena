---
name: financial-math
description: Python patterns for financial calculations on Treasury data.
---

# Financial Math

Always use Python. Common patterns:

```python
# Percent change
python3 -c "print(((new - old) / old) * 100)"

# CAGR
python3 -c "print(((end/start)**(1/years) - 1) * 100)"

# Statistics (population std dev is default)
python3 -c "import statistics; print(statistics.pstdev([1,2,3]))"
python3 -c "import statistics; print(statistics.mean([1,2,3]))"

# Pearson correlation
python3 -c "
x=[1,2,3]; y=[4,5,6]
n=len(x); mx=sum(x)/n; my=sum(y)/n
cov=sum((a-mx)*(b-my) for a,b in zip(x,y))/n
sx=(sum((a-mx)**2 for a in x)/n)**0.5
sy=(sum((b-my)**2 for b in y)/n)**0.5
print(cov/(sx*sy))
"
```

## Linear Regression (OLS)
```python
python3 -c "
import numpy as np
x = np.array([1960, 1961, 1962, 1963, 1964])
y = np.array([100.5, 102.3, 105.1, 107.8, 110.2])
# OLS: y = slope*x + intercept
n = len(x)
slope = (n*np.dot(x,y) - x.sum()*y.sum()) / (n*(x**2).sum() - x.sum()**2)
intercept = (y.sum() - slope*x.sum()) / n
r_squared = 1 - np.sum((y - slope*x - intercept)**2) / np.sum((y - y.mean())**2)
print(f'slope={slope:.4f}, intercept={intercept:.4f}, R²={r_squared:.4f}')
# Predict: slope * new_x + intercept
"
```

## Decay Factor / Growth Rate
```python
# Exponential decay: final = initial * (1 + rate)^years
python3 -c "
import math
initial = 1000; final = 1200; years = 5
rate = (final/initial)**(1/years) - 1
print(f'Annual growth rate: {rate*100:.2f}%')
"
```

## Quartiles / IQR / H-Spread
```python
# Use numpy for quartiles (most compatible with expected answers)
python3 -c "
import numpy as np
data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
q1 = np.percentile(data, 25)
q3 = np.percentile(data, 75)
iqr = q3 - q1  # H-spread = IQR
print(f'Q1={q1}, Q3={q3}, IQR={iqr}')
"
# If numpy unavailable, use statistics.quantiles (exclusive method)
python3 -c "
import statistics
data = [1,2,3,4,5,6,7,8,9,10,11,12]
q = statistics.quantiles(data, n=4)  # returns [Q1, Q2, Q3]
print(f'Q1={q[0]}, Q3={q[2]}, IQR={q[2]-q[0]}')
"
```

## Number Parsing
- `1,590` → 1590 (remove commas)
- `(123)` → -123 (accounting negative)
- `---` or `...` → no data

## Precision
- Follow EXACTLY what the question asks: "nearest tenth" = 1 decimal, "nearest hundredth" = 2 decimals
- When converting units: "in millions" means divide thousands by 1000
- If question says "in millions" and table says "in thousands", convert: value_thousands / 1000

## Answer Format
Plain number to `/app/answer.txt`. No $, %, commas. Use `-` for negatives.
