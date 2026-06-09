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

## Number Parsing
- `1,590` → 1590 (remove commas)
- `(123)` → -123 (accounting negative)
- `---` or `...` → no data

## Answer Format
Plain number to `/app/answer.txt`. No $, %, commas. Use `-` for negatives.
