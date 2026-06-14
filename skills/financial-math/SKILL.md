---
name: financial-math
description: Common financial calculation patterns and formulas for Treasury Bulletin data analysis.
---

# Financial Math Reference

## Common Calculations

### Percent Change
```python
pct_change = ((new_val - old_val) / old_val) * 100
```

### Average Over Years
```python
values = [v1, v2, v3, v4]
avg = sum(values) / len(values)
```

### Compound Annual Growth Rate (CAGR)
```python
cagr = ((end_val / start_val) ** (1 / n_years) - 1) * 100
```

### Share/Percentage of Total
```python
share = (part / total) * 100
```

### Year-over-Year Change
```python
yoy_change = new_val - old_val
```

### Cumulative Sum Over Range
```python
total = sum(annual_values)  # sum all years in range
```

## Statistical Analysis (pure stdlib — no numpy needed)

Many questions need real statistics, not just arithmetic. Use `math` and `statistics`.

### Geometric Mean
```python
import math
vals = [v1, v2, v3]            # all must be > 0
gm = math.exp(sum(math.log(v) for v in vals) / len(vals))
```

### Linear Regression / Trend Fit (OLS, y = slope*x + intercept)
Returns the coefficients many "fit a linear model / trend" questions ask for.
```python
xs = [1929, 1930, 1931]        # e.g. fiscal years
ys = [1.2, 1.5, 1.9]           # e.g. receipts in billions
n = len(xs)
mx = sum(xs)/n; my = sum(ys)/n
slope = sum((x-mx)*(y-my) for x,y in zip(xs,ys)) / sum((x-mx)**2 for x in xs)
intercept = my - slope*mx
print(f"slope={slope:.4f} intercept={intercept:.4f}")
# Some questions index x from 0,1,2,... instead of by year — read carefully.
```

### Pearson Correlation
```python
import statistics
r = statistics.correlation(xs, ys)   # Python 3.10+
```

### Box-Cox Transform
For a value x>0 and parameter lambda (λ):
```python
import math
def boxcox(x, lam):
    return (x**lam - 1)/lam if lam != 0 else math.log(x)
# "difference between Box-Cox transformed values" = boxcox(a,lam) - boxcox(b,lam)
```

### Median, Quartiles, IQR, Std Dev
```python
import statistics
med = statistics.median(vals)
q1, q2, q3 = statistics.quantiles(vals, n=4)   # default method='exclusive'
iqr = q3 - q1
pstdev = statistics.pstdev(vals)   # population
sstdev = statistics.stdev(vals)    # sample
```
If a question specifies a quartile/percentile METHOD, match it (e.g. `statistics.quantiles(vals, n=4, method='inclusive')`).

## Number Parsing

Treasury tables use these formats:
- `1,590` → 1590 (thousands separator)
- `(123)` → -123 (accounting negative)
- `---` or `...` → no data
- `*` → footnote, check below table
- `1/` → footnote indicator

## Unit Conversion

If question asks in different units than the table:
```python
# Table in millions, answer needed in billions
answer_billions = value_millions / 1000

# Table in thousands, answer needed in millions
answer_millions = value_thousands / 1000
```

## Answer Format

Write the answer to /app/answer.txt with these conventions:
- Pure numbers: just the number (e.g., "2025191")
- Percentages: just the number without % (e.g., "5.2")
- Negative values: use minus sign (e.g., "-123")
- Dates: as text (e.g., "March 1977")
- No commas in numbers
- No dollar signs or unit labels
