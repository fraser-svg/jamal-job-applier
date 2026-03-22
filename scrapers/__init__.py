from scrapers.indeed import scrape_indeed
from scrapers.reed import scrape_reed
from scrapers.s1jobs import scrape_s1jobs
from scrapers.totaljobs import scrape_totaljobs
from scrapers.caterer import scrape_caterer
from scrapers.cvlibrary import scrape_cvlibrary

ALL_SCRAPERS = [
    ("Indeed", scrape_indeed),
    ("Reed", scrape_reed),
    ("S1Jobs", scrape_s1jobs),
    ("Totaljobs", scrape_totaljobs),
    ("Caterer", scrape_caterer),
    ("CV-Library", scrape_cvlibrary),
]
