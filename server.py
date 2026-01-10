from fastapi import FastAPI
from pydantic import BaseModel
import threading
import os

from scrapers.scrape_willhaben_async import run_scrape
import market_analysis

app = FastAPI()

class ScrapeRequest(BaseModel):
    url: str
    headless: bool = True
    workers: int = 4

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/scrape")
def start_scrape(req: ScrapeRequest):
    def job():
        os.environ["MAX_WORKERS"] = str(req.workers)
        run_scrape(req.url, log_cb=print, headless=req.headless)

    threading.Thread(target=job, daemon=True).start()
    return {"status": "started"}

@app.post("/analyze")
def analyze():
    market_analysis.main()
    return {"status": "analysis_done"}
