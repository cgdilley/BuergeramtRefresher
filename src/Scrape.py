from __future__ import annotations

import httpx
import locale
from lxml.html import HtmlElement as Element, XHTMLParser, fromstring
from ratelimit import limits, sleep_and_retry
import re
from datetime import datetime, date, timedelta
import winsound
import time
from typing import NamedTuple, Hashable
import webbrowser

PAGE = r"https://tempus-termine.com/termine/index.php?sna=T95dd93726ccb87c3bdae46abc8d6f583&anr=107&allestandorte=1&action=open&page=tagesauswahl&tasks=4787&kuerzel=PARPEINBUE&schlangen=1-2-3-12-13&standortrowid=298"
REFRESH_RATE = 30

# day_parser = re.compile(r"^Termine +am +([0-9]+)\. +([A-Za-zäöüÄÖÜ]+)$")

today = date.today()

COUNT = 0


def main():
    last_found: set[FreeDate] = set()
    while True:
        found = refresh()
        if last_found != found and len(last_found) > 0:
            print("\nCHANGES DETECTED:  " + ", ".join(x.day.strftime("%d.%m") for x in found.difference(last_found)))
            winsound.Beep(220, 250)
            time.sleep(0.25)
            winsound.Beep(220, 500)
        important = False
        for day in found:
            if day.day - today < timedelta(days=1):
                webbrowser.open(day.full_link)
                print("\n !!!  APPOINTMENT TODAY  !!! " + day.day.strftime("%d.%m"))
                for _ in range(5):
                    winsound.Beep(880, 150)
                    time.sleep(0.1)
            elif day.day - today < timedelta(days=14):
                print("\n -- NEARBY TIME: " + day.day.strftime("%d.%m"))
                important = True
        if important:
            winsound.Beep(440, 1000)

        last_found = found


class FreeDate(NamedTuple):
    day: date
    link: str

    @property
    def full_link(self) -> str:
        return f"https://tempus-termine.com/termine/index.php{self.link}"

    def __hash__(self) -> int:
        return hash(self.day)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, FreeDate):
            return self.day == other.day
        return False

@sleep_and_retry
@limits(calls=1, period=REFRESH_RATE)
def refresh() -> set[FreeDate]:
    locale.setlocale(locale.LC_TIME, "de_DE.UTF-8")

    found: set[FreeDate] = set()
    root = parse_html(PAGE)
    global COUNT
    COUNT += 1
    print(f"\rrefreshing ({COUNT})...", end="")

    free = root.xpath("//div[@id='kalender']//td[@class='monatevent']")

    for day in free:
        a = day.xpath(".//a")[0]
        title = a.attrib.get("title")
        try:
            d = datetime.strptime(title, "Termine am  %d. %B").replace(year=today.year).date()
            found.add(FreeDate(day=d, link=a.attrib["href"]))
        except:
            print("Could not parse date: " + title)

    return found





#


IMG_REGEX = re.compile(r"(<(source|img)[^>]+)>")


def parse_html(url: str) -> Element:
    response = httpx.get(url.strip())
    if response.status_code != 200:
        raise Exception("Error")
    text = response.text
    text = text.replace("<br>", "<br/>").replace("<hr>", "hr/>")
    text = IMG_REGEX.sub("\1/>", text)
    parser = XHTMLParser(recover=True, huge_tree=True)
    return fromstring(text, parser=parser)


if __name__ == '__main__':
    main()
