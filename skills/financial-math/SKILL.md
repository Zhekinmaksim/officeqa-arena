---
name: financial-math
description: Financial and statistical calculation patterns for Treasury Bulletin data analysis.
---

# Financial Math & Statistics Reference

## ALWAYS use Python for calculations. Import statistics module when needed.

### Basic Financial
```python
# Percent change
pct = ((new - old) / old) * 100

# CAGR (Compound Annual Growth Rate)
cagr = ((end / start) ** (1 / years) - 1) * 100

# Share / Percentage of total
share = (part / total) * 100

# Absolute difference
diff = abs(a - b)
```

### Statistics (import statistics)
```python
import statistics

# Mean / Average
mean = statistics.mean(values)

# Population standard deviation (DEFAULT for "standard deviation")
pstd = statistics.pstdev(values)

# Sample standard deviation (ONLY if question says "sample")
sstd = statistics.stdev(values)

# Population variance (DEFAULT for "variance")
pvar = statistics.pvariance(values)

# Sample variance
svar = statistics.variance(values)

# Median
med = statistics.median(values)
```

### Pearson Correlation
```python
def pearson(x, y):
    n = len(x)
    mx, my = sum(x)/n, sum(y)/n
    cov = sum((a-mx)*(b-my) for a,b in zip(x,y)) / n
    sx = (sum((a-mx)**2 for a in x) / n) ** 0.5
    sy = (sum((b-my)**2 for b in y) / n) ** 0.5
    return cov / (sx * sy) if sx*sy else 0

r = pearson(x_values, y_values)
```

### Arc Elasticity (Midpoint Method)
```python
arc_e = ((q2-q1)/((q2+q1)/2)) / ((p2-p1)/((p2+p1)/2))
```

### Decay Factor
```python
# Annual decay factor = 1 + growth_rate (when negative growth)
decay = (end / start) ** (1 / years)
```

## Number Parsing from Tables

- `1,590` → 1590 (remove commas)
- `(123)` → -123 (accounting negative)
- `---` or `...` → no data
- `*` or `1/` → footnote
- `nan` → missing data

## Answer Format

Write to `/app/answer.txt`:
- Pure number, no units, no $, no commas
- Negative: use minus sign `-123`
- No % sign for percentages
- Match requested decimal places exactly
