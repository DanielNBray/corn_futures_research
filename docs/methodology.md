#### So the goal of this project is to use databento api to research corn futures. 

## STEP 1: Get data
part of this step is to learn the best way to store this data, what type of data I want, and how to actually collect the data using the api.

The chosen schema is level 3 data, specifically market by order (MBO) as it provides data on every order book event across every price level - the highest level of granularity. While this data is SUPER overkill for the firts few projects I will complete, it can be simplifed for my simple models and also allows me to do more complex models later on with the same data. In other words, this extensive data contains the simple data within it, but also does not restrict me when completing more extensive models later on.

Costs for this: $63.59 USD for [2024-02-04 -> 2026-02-06] @ MBO ($1.80/GB) = 37.9GB

The issue now is that all the code examples and tutorials in the databento docs use the API and some variation of client.timeseries.get_range(...), while I'm stuck with a zip file that contains 629 zip files inside which all contain a single .dbn file that holds corn futures data for a particular day. Anyways, I need to find a way to write a program that can use this data the exact same way as the databento api.

Except, since the data is ~40GB and my laptop only has 16GB of memory, I have to think of a sophisticated way to handle the data, especially since I will perform lots of models and operations on it.

Anyways, to unzip the 629 files, I ran this single purpose script that places the unzipped files into a new folder, and than I manually deleted the old folder:
```python
import zstandard as zstd
from pathlib import Path

raw = Path(r"C:\Users\dannb\_projects\code\active\corn_futures_research\data\raw")
out = Path(r"C:\Users\dannb\_projects\code\active\corn_futures_research\data\zipped_raw")
out.mkdir(exist_ok=True)

for zst_file in raw.glob("*.zst"):
    print(f"Unzipping {zst_file.name}...")
    with open(zst_file, 'rb') as f:
        dctx = zstd.ZstdDecompressor()
        with open(out / zst_file.stem, 'wb') as out_f:
            dctx.copy_stream(f, out_f)

```

## STEP 2: Display
display the data as a time series plot using matplotlib.

## STEP 3: Display 2 EMA lines on a plot of price
This will require researching how to calculate ema, and how to display it.

## STEP 4: Forward Curve
learn what the forward curve is, and attempt to calculate and display it using the data at hand.
