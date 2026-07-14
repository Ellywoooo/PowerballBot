"""
Predictor for the Powerball lottery.
load_draws()           → read CSV, clean columns, sort by date
compute_main_scores()  → freq + recency + gap → main_score Series
compute_powerball_scores() → same for powerball 1–10
passes_filters()       → odd/even + consecutive rules (from notebook)
generate_lines()       → combos → filter → pick diverse lines + PB
main()                 → wire it together, print results

Flow:
df = load_draws()
main_score = compute_main_scores(df)
powerball_score = compute_powerball_scores(df)
lines = generate_lines(main_score, powerball_score)
print(lines)
"""

import numpy as np
import pandas as pd
import config
from itertools import combinations # for generating combinations of numbers.

# Load the draws from the CSV file.
# Input: path to the CSV file.
# Process:
# 1. Read the CSV file.
# 2. Convert the draw_date column to datetime.
# 3. Sort the DataFrame by draw_date.
# 4. Return the DataFrame.
# Output: pandas DataFrame sorted from oldest to newest.
def load_draws(path=config.DATA_PATH):
    column_names = [
        "draw_number", "draw_date",
        "main_1", "main_2", "main_3", "main_4", "main_5", "main_6",
        "bonus", "powerball",
    ]
    df = pd.read_csv(path, header=0, names=column_names)
    df["draw_date"] = pd.to_datetime(df["draw_date"])
    df = df.sort_values("draw_date").reset_index(drop=True)
    return df

# Scale the series to 0-1.
# Input: pandas Series.
# Process:
# 1. Find the minimum and maximum values of the series.
# 2. Scale the series to 0-1.
# 3. Return the scaled series.
# Output: pandas Series scaled to 0-1. So frequency, recency, gap can be combined fairly.
def min_max_scale(series):
    lo = series.min()
    hi = series.max()
    return series * 0 + 0.5 if hi == lo else (series - lo) / (hi - lo)


# Calculate the last seen gap for a given number.
# Input: number, pandas DataFrame, columns.
# Process:
# 1. Iterate through the DataFrame from the last row to the first row.
# 2. Check if the number is in the row.
# 3. Return the gap between the last seen number and the current number.
# Output: int, the last seen gap.
def last_seen_gap(number, dataframe, columns):
    for i in range(len(dataframe) - 1, -1, -1):
        row = dataframe.iloc[i][columns]
        if number in row.values:
            return (len(dataframe) - 1) - i
    return len(dataframe)

# Compute the main scores.
# Input: pandas DataFrame.
# Process:
# 1. Compute the frequency of each number.
# 2. Compute the recency of each number.
# 3. Compute the gap of each number.
# 4. Return the main scores.
# Output: pandas Series, the main scores.
def compute_main_scores(df):
    # --- Frequency (all draws) ---
    all_main = df[config.MAIN_COLUMNS].values.flatten()
    freq = pd.Series(all_main).value_counts().sort_index()

    # --- Recency (last N draws) ---
    recent_df = df.tail(config.RECENT_DRAWS)
    recent_main = recent_df[config.MAIN_COLUMNS].values.flatten()
    recent_freq = pd.Series(recent_main).value_counts()

    all_time_rate = freq / len(df)
    recent_rate = recent_freq / len(recent_df)
    recent_rate = recent_rate.reindex(range(1, 41), fill_value=0)

    # --- Gap (draws since last seen) ---
    gaps = {n: last_seen_gap(n, df, config.MAIN_COLUMNS) for n in range(1, 41)}
    gap_series = pd.Series(gaps)

    # --- Normalize + combine ---
    freq_score = min_max_scale(freq)
    recency_score = min_max_scale(recent_rate)
    gap_score = min_max_scale(gap_series)

    return (
        config.WEIGHT_FREQ * freq_score
        + config.WEIGHT_RECENCY * recency_score
        + config.WEIGHT_GAP * gap_score
    )

# Compute the powerball scores.
# Input: pandas DataFrame.
# Process:
# 1. Compute the frequency of each powerball number.
# 2. Compute the recency of each powerball number.
# 3. Compute the gap of each powerball number.
# 4. Return the powerball scores.
# Output: pandas Series, the powerball scores.
def compute_powerball_scores(df):
    # --- Frequency (all draws) ---
    freq = df["powerball"].value_counts().sort_index()

    # --- Recency (last N draws) ---
    recent_df = df.tail(config.RECENT_DRAWS)
    recent_freq = recent_df["powerball"].value_counts()
    recent_rate = (recent_freq / len(recent_df)).reindex(range(1, 11), fill_value=0)

    # --- Gap (draws since last seen) ---
    gaps = {n: last_seen_gap(n, df, ["powerball"]) for n in range(1, 11)}
    gap_series = pd.Series(gaps)

    # --- Normalize + combine ---
    freq_score = min_max_scale(freq)
    recency_score = min_max_scale(recent_rate)
    gap_score = min_max_scale(gap_series)

    return (
        config.WEIGHT_FREQ * freq_score
        + config.WEIGHT_RECENCY * recency_score
        + config.WEIGHT_GAP * gap_score
    )

# Count the number of odd numbers in the list.
def count_odd(numbers):
    return sum(n % 2 == 1 for n in numbers)

# Check if the number of odd numbers is not 0 or 6.
# Mixing odd and even numbers is good.
def valid_odd_even(numbers):
    odd = count_odd(numbers)
    return odd not in (0, 6)

# Find the maximum consecutive run of numbers in the list.
# Like 1, 2, 3, 4 is a consecutive run of 4.
def max_consecutive_run(numbers):
    sorted_nums = sorted(numbers)
    max_run = 1
    current_run = 1
    for i in range(1, len(sorted_nums)):
        if sorted_nums[i] == sorted_nums[i - 1] + 1:
            current_run += 1
            max_run = max(max_run, current_run)
        else:
            current_run = 1
    return max_run

# Reject lines with more than 3 consecutive numbers.
def valid_consecutive(numbers):
    return max_consecutive_run(numbers) < 4

# Both odd/even and consecutive rules must be satisfied.
def passes_filters(numbers):
    return valid_odd_even(numbers) and valid_consecutive(numbers)
# Turn a row into a list of 6 numbers.
def _mains_from_row(row):
    return [int(row[c]) for c in ["m1", "m2", "m3", "m4", "m5", "m6"]]

# Check if the new line is too similar to the lines we already picked.
def _too_similar(mains, chosen, max_shared=config.MAX_SHARED):
    return any(len(set(mains) & set(prev)) > max_shared for prev in chosen)

# Generate the lines.
# Input: main_score, powerball_score, optional seed.
# Process:
# 1. Take top CANDIDATE_POOL_SIZE numbers by score.
# 2. Generate 6-number combos, keep those that pass filters.
# 3. Sort by score, keep top SAMPLE_POOL_SIZE as the sampling pool.
# 4. Weighted-random sample without replacement (higher score → higher chance),
#    rejecting combos that are too similar to ones already chosen.
# 5. Assign Powerballs randomly from the top Powerball candidates.
# Output: pandas DataFrame of NUM_LINES lines.
def generate_lines(main_score, powerball_score, seed=None):
  rng = np.random.default_rng(seed)

  candidates = main_score.sort_values(ascending=False).head(config.CANDIDATE_POOL_SIZE).index.tolist()

  rows = []
  for combo in combinations(candidates, 6):
    mains = sorted(combo)
    if not passes_filters(mains):
      continue
    rows.append({
      "score": main_score.loc[list(combo)].sum(),
      "m1": mains[0], "m2": mains[1], "m3": mains[2],
      "m4": mains[3], "m5": mains[4], "m6": mains[5],
    })

  combo_df = (
    pd.DataFrame(rows)
    .sort_values("score", ascending=False)
    .reset_index(drop=True)
  )

  chosen_mains = []
  pool_start = 0

  # Prefer the top SAMPLE_POOL_SIZE by score, but expand deeper when
  # diversity (_too_similar) leaves us short of NUM_LINES.
  while len(chosen_mains) < config.NUM_LINES and pool_start < len(combo_df):
    available = (
      combo_df
      .iloc[pool_start:pool_start + config.SAMPLE_POOL_SIZE]
      .copy()
      .reset_index(drop=True)
    )
    pool_start += config.SAMPLE_POOL_SIZE

    while len(chosen_mains) < config.NUM_LINES and len(available) > 0:
      weights = available["score"].to_numpy(dtype=float)
      if weights.sum() <= 0:
        weights = np.ones(len(available), dtype=float)
      probs = weights / weights.sum()

      idx = int(rng.choice(len(available), p=probs))
      mains = _mains_from_row(available.iloc[idx])

      if mains not in chosen_mains and not _too_similar(mains, chosen_mains):
        chosen_mains.append(mains)

      available = available.drop(available.index[idx]).reset_index(drop=True)

  top_pbs = powerball_score.sort_values(ascending=False).head(5).index.to_numpy()

  final_rows = []
  for i, mains in enumerate(chosen_mains):
    pb = int(rng.choice(top_pbs))
    final_rows.append({
      "line_no": i + 1,
      "line": " ".join(f"{n:02d}" for n in mains),
      "powerball": pb,
      "score": main_score.loc[mains].sum(),
    })

  return pd.DataFrame(final_rows)

# Main function to run the predictor.
# Input: None.
# Process:
# 1. Load the draws.
# 2. Compute the main and powerball scores.
# 3. Generate the lines.
# 4. Print the lines.
# Output: None.
def main():
  df = load_draws()
  main_score = compute_main_scores(df)
  powerball_score = compute_powerball_scores(df)
  lines = generate_lines(main_score, powerball_score)

  print("NZ Lotto Powerball Suggestions\n")
  for _, row in lines.iterrows():
    print(f"{int(row['line_no'])}. {row['line']} + PB {int(row['powerball'])}")
  print("\nStatistical analysis only - does not guarantee a win.")


if __name__ == "__main__":
  main()