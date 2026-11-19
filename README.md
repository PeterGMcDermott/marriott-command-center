# Marriott Command Center

An always-on ambient dashboard for a vertically mounted widescreen monitor, built to sit behind me on video calls.

Live: https://petergmcdermott.github.io/marriott-command-center/

`index.html` is the ambient edition. `classic.html` is the original version.

It shows Marriott stock, headlines, and weekend hotel rates for five cities, and refreshes on every load. Stocks update live via Yahoo Finance; headlines come from `data/news.json`. Weekend rates are refreshed weekly, by hand, since Marriott has no public API. Meeting Mode hides the rates on HQ calls.

Runs on Chromecast with Google TV and Fully Kiosk Browser.
