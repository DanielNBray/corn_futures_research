#### So the goal of this project is to use databento api to research corn futures. 

## STEP 1: Get data
part of this step is to learn the best way to store this data, what type of data I want, and how to actually collect the data using the api.

The chosen schema is level 3 data, specifically market by order (MBO) as it provides data on every order book event across every price level - the highest level of granularity. While this data is SUPER overkill for the firts few projects I will complete, it can be simplifed for my simple models and also allows me to do more complex models later on with the same data. In other words, this extensive data contains the simple data within it, but also does not restrict me when completing more extensive models later on.

Costs for this: $63.59 USD for [2024-02-04 -> 2026-02-06] @ MBO ($1.80/GB) = 37.9GB

Here is what the data looks like (using 5th Feb 2024 daily data):
Input:
```python
import databento as db
corn_dbn_file  = db.DBNStore.from_file(r"C:\Users\dannb\_projects\code\active\Researching_CornFutures\corndata_unzippled_db\glbx-mdp3-20240205.mbo.dbn")
corn_book_df  = corn_dbn_file.to_df()
corn_book_df 
```
Output:
![Image of sample data visualised in dataframe format](./images/raw_daily_data_view_20240205.png)

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
Before I begin, it is probably best to describe what a corn futures contract is. A futures contract is the obligation between a buyer and seller (of corn) to buy/sell corn at the current market price at a set quantity at a future date. And while these financial instruments are intended for farmers and businesses who use corn to hedge risks of corn prices falling/rising; it can be used for speculative purposes - to predict price action and make a profit doing so.

Price action is simple for corn, relative to other assets like cash rate or equities. It is broken down into supply (higher = lower price) and demand (higher = higher price). 

Supply is influenced by production (weather, agri-tech), transport, storage, cost of alternative crops (influences a farmers decision to plant corn, or plant something like soybean if it can be sold for higher price).

Demand is influenced by the demand of corns by products: sweetner (HFCS), cornstarch, Biofuel (ethonol), Live-stock. And therefore this demand can be extrapolated by price movements in companies that rely heavily on these by products. For example, an increase in Pepsi's market cap as a result of an increase in demand for pepsi drinks would indicate a higher demand for sweetner which would result in a higher demand for CORN!!


For the first step, visualising the data, I will use the front month futures contract as the representation of the price of corn at a given time. This is because corn futures is in contango, meaning later expiring contracts are priced higher to account for storage and financing costs embedded in defferred contracts. And the front-month contract minimises this variable and more closely represents what someone would buy/sell corn for at a given time.










```bash
python scripts/process_all_data.py --data-dir data/raw --output data/processed/front_month_trades.parquet
```

## STEP 2: Display
display the data as a time series plot using matplotlib.

## STEP 3: Display 2 EMA lines on a plot of price
This will require researching how to calculate ema, and how to display it.

## STEP 4: Forward Curve
learn what the forward curve is, and attempt to calculate and display it using the data at hand.
