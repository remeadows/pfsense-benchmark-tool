import pandas as pd

file_path = "c:/Pfsense_Benchmark_Tool/Pf Sense Benchmark.xlsx"

df = pd.read_excel(file_path, header=None)  # <---- IMPORTANT: no header

print("===== FIRST 20 ROWS =====")
for idx, row in df.head(20).iterrows():
    print(idx, row.tolist())
