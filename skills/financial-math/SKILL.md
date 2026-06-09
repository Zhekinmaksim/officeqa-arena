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
