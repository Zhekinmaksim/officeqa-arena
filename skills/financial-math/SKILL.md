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
- Lists of values: `[v1, v2, v3]` — ALWAYS use space after each comma
- Match the question's scale: if table says "in millions" but question asks for "nominal dollars", multiply by 1000000
