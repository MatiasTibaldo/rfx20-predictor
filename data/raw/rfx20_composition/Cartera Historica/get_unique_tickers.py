import os
import glob
import csv

directory = '/home/mtibaldo/MCD/ProyectoFinal/data rfx20/Cartera Historica/'
csv_files = glob.glob(os.path.join(directory, '*.csv'))

unique_tickers = set()

for file_path in csv_files:
    with open(file_path, mode='r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=';')
        try:
            header = next(reader)
        except StopIteration:
            continue
        
        for row in reader:
            if row:
                unique_tickers.add(row[0])

sorted_tickers = sorted(list(unique_tickers))

output_file = os.path.join(directory, 'unique_tickers.txt')
with open(output_file, 'w', encoding='utf-8') as f:
    for ticker in sorted_tickers:
        f.write(f"{ticker}\n")

print(f"Unique tickers found ({len(sorted_tickers)}):")
for ticker in sorted_tickers:
    print(ticker)
print(f"\nSaved to: {output_file}")
