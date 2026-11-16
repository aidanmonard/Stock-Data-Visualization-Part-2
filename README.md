# Stock-Data-Visualization-Part-2

A Flask web application that retrieves historical stock prices from Alpha Vantage, filters the results by date, and displays a chart below the input form. The app can run locally or inside Docker.

## Features
- S&P 500 stock symbol dropdown populated from a public CSV when the page loads.
- Optional local `stocks.csv` file: place it beside `app.py` to use the provided course CSV instead.
- Weekly and monthly Alpha Vantage time series.
- Line and bar charts
- Beginning and ending date inputs with date-range validation.
- Chart is displayed directly below the form.
- User-friendly errors for missing API keys, API limits, invalid input, and network failures.

## Run locally (Mac)
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export ALPHA_VANTAGE_API_KEY="your_api_key"
python app.py
```
Open http://localhost:5001 in your browser.

Get an API key from https://www.alphavantage.co/support/#api-key. Keep it private.

## Run with Docker Compose
1. Install and start Docker Desktop.
2. In the project directory, set the API key in your terminal:
```bash
export ALPHA_VANTAGE_API_KEY="your_api_key"
```
3. Build and start the container:
```bash
docker compose up --build 
```
4. Open http://localhost:5001.
5. Stop the container with Ctrl+C, then run:
```bash
docker compose down
```

## Stock symbol list
The app downloads the S&P 500 constituents CSV from:
https://github.com/datasets/s-and-p-500-companies

If your instructor supplied `stocks.csv`, unzip it and place the CSV beside `app.py`. The app checks for that local file first. If neither source is available, a small fallback list keeps the page from crashing.

## Important
Alpha Vantage free-tier request limits and available functions can change. If you receive an API limit message, wait and try again or check Alpha Vantage's current documentation. The stock list and stock-price API both require internet access.

## Project files
- `app.py`: Flask routes, stock list loading, API requests, date filtering, chart generation.
- `templates/index.html`: HTML form and chart display.
- `Dockerfile`: image build instructions.
- `docker-compose.yml`: container configuration.
- `requirements.txt`: Python dependencies.
