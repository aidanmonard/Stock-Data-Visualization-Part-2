import os
from datetime import datetime
from io import BytesIO
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"

SP500_CSV_URL = (
    "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/"
    "master/data/constituents.csv"
)

TIME_SERIES = {
    "weekly": ("Weekly", "TIME_SERIES_WEEKLY", "Weekly Time Series"),
    "monthly": ("Monthly", "TIME_SERIES_MONTHLY", "Monthly Time Series"),
}

CHART_TYPES = {
    "line": "Line",
    "bar": "Bar",
}


def parse_date(value):
  
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
        if parsed.strftime("%Y-%m-%d") != value:
            raise ValueError
        return parsed
    except (TypeError, ValueError):
        raise ValueError("Dates must use YYYY-MM-DD format.")


def load_stock_symbols():
    
    local_csv = Path(__file__).parent / "stocks.csv"
    try:
        if local_csv.exists():
            stocks = pd.read_csv(local_csv)
        else:
            response = requests.get(SP500_CSV_URL, timeout=15)
            response.raise_for_status()
            stocks = pd.read_csv(BytesIO(response.content))

        symbol_column = next(
            (column for column in stocks.columns
             if column.strip().lower() in {"symbol", "ticker", "symbol/ticker"}),
            None,
        )
        if symbol_column is None:
            raise ValueError("The stock CSV does not contain a symbol column.")

        name_column = next(
            (column for column in stocks.columns
             if column.strip().lower() in {"name", "security", "company"}),
            None,
        )

        options = []
        for _, row in stocks.iterrows():
            symbol = str(row[symbol_column]).strip().replace(".", "-")
            if not symbol or symbol.lower() == "nan":
                continue
            name = str(row[name_column]).strip() if name_column else symbol
            if name.lower() == "nan":
                name = symbol
            options.append({"symbol": symbol, "name": name})

        return sorted(options, key=lambda item: item["symbol"])
    except (requests.RequestException, ValueError, pd.errors.ParserError, OSError):
       
        return [
            {"symbol": "AAPL", "name": "Apple Inc."},
            {"symbol": "MSFT", "name": "Microsoft Corporation"},
            {"symbol": "AMZN", "name": "Amazon.com, Inc."},
            {"symbol": "GOOGL", "name": "Alphabet Inc."},
            {"symbol": "NVDA", "name": "NVIDIA Corporation"},
            {"symbol": "META", "name": "Meta Platforms, Inc."},
            {"symbol": "BRK-B", "name": "Berkshire Hathaway"},
            {"symbol": "JPM", "name": "JPMorgan Chase & Co."},
        ]


def get_stock_data(symbol, function, api_key):
    response = requests.get(
        ALPHA_VANTAGE_URL,
        params={"function": function, "symbol": symbol, "apikey": api_key},
        timeout=30,
    )
    response.raise_for_status()
    result = response.json()

    if "Error Message" in result:
        raise ValueError(result["Error Message"])
    if "Note" in result or "Information" in result:
        raise ValueError(
            result.get("Note") or result.get("Information")
        )

    series_key = next(
        (item[2] for item in TIME_SERIES.values() if item[1] == function),
        None,
    )
    if not series_key or series_key not in result:
        raise ValueError(
            "No stock data was returned. Check the symbol, API key, "
            "and Alpha Vantage usage limits."
        )

    data = pd.DataFrame.from_dict(result[series_key], orient="index")
    data.index = pd.to_datetime(data.index)
    data.index.name = "Date"
    data = data.sort_index()
    data.rename(
        columns={
            "1. open": "Open",
            "2. high": "High",
            "3. low": "Low",
            "4. close": "Close",
            "5. volume": "Volume",
        },
        inplace=True,
    )

    for column in ["Open", "High", "Low", "Close", "Volume"]:
        if column in data.columns:
            data[column] = pd.to_numeric(data[column], errors="coerce")

    if "Close" not in data.columns:
        raise ValueError("The API response did not contain closing prices.")
    return data.dropna(subset=["Close"])

def make_chart(data, symbol, chart_type, start, end):
    if data.empty:
        raise ValueError("No trading data was found in the selected date range.")

    fig, axis = plt.subplots(figsize=(11, 5))
    if chart_type == "line":
        axis.plot(data.index, data["Close"], marker="o", markersize=2)
        axis.set_ylabel("Closing Price (USD)")
    elif chart_type == "bar":
        axis.bar(data.index, data["Close"], width=0.8)
        axis.set_ylabel("Closing Price (USD)")
    else:
        plt.close(fig)
        raise ValueError("Select a valid chart type.")

    axis.set_title(f"{symbol} Stock Prices: {start:%Y-%m-%d} to {end:%Y-%m-%d}")
    axis.set_xlabel("Date")
    axis.grid(True, alpha=0.25)
    axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    fig.autofmt_xdate()
    fig.tight_layout()

    image = BytesIO()
    fig.savefig(image, format="png", dpi=140, bbox_inches="tight")
    plt.close(fig)
    image.seek(0)
    import base64
    return base64.b64encode(image.read()).decode("utf-8")


@app.route("/", methods=["GET", "POST"])
def index():
    stocks = load_stock_symbols()
    chart_image = None
    error = None
    selected = {
        "symbol": "",
        "chart_type": "line",
        "time_series": "weekly",
        "start_date": "",
        "end_date": "",
    }

    if request.method == "POST":
        selected.update({
            "symbol": request.form.get("symbol", "").strip().upper(),
            "chart_type": request.form.get("chart_type", "line"),
            "time_series": request.form.get("time_series", "weekly"),
            "start_date": request.form.get("start_date", "").strip(),
            "end_date": request.form.get("end_date", "").strip(),
        })

        try:
            if selected["chart_type"] not in CHART_TYPES:
                raise ValueError("Choose a valid chart type.")
            if selected["time_series"] not in TIME_SERIES:
                raise ValueError("Choose a valid time series.")
            if not any(s["symbol"] == selected["symbol"] for s in stocks):
                raise ValueError("Choose a stock from the stock symbol list.")

            start = parse_date(selected["start_date"])
            end = parse_date(selected["end_date"])
            if end < start:
                raise ValueError("The end date cannot be before the beginning date.")

            api_key = os.getenv("ALPHA_VANTAGE_API_KEY", "").strip()
            if not api_key:
                raise ValueError(
                    "The Alpha Vantage API key is not configured. "
                    "Set ALPHA_VANTAGE_API_KEY in your environment."
                )

            function = TIME_SERIES[selected["time_series"]][1]
            data = get_stock_data(selected["symbol"], function, api_key)
            data = data.loc[(data.index >= start) & (data.index <= end)]
            chart_image = make_chart(
                data, selected["symbol"], selected["chart_type"], start, end
            )

        except requests.RequestException:
            error = "Could not connect to the stock data service. Please try again."
        except (ValueError, KeyError) as exc:
            error = str(exc)
        except Exception:
            app.logger.exception("Unexpected error while creating stock chart")
            error = "Something went wrong while creating the chart. Please try again."

    return render_template(
        "index.html",
        stocks=stocks,
        chart_image=chart_image,
        error=error,
        selected=selected,
        chart_types=CHART_TYPES,
        time_series=TIME_SERIES,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
