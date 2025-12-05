import pandas as pd

file_path = "c:/Pfsense_Benchmark_Tool/Pf Sense Benchmark.xlsx"

df = pd.read_excel(file_path)

print("===== LOADED BENCHMARK =====")
print(df.head())

print("\n===== COLUMN NAMES FOUND =====")
print(df.columns.tolist())

print("\n===== TOTAL ROWS =====")
print(len(df))