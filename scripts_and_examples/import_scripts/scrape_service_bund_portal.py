import datetime
import json
import random
import time
from pprint import pprint

import pydantic
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

from data_backend_client import check_pk_existence, insert_many

base_url = "https://www.service.bund.de/"

DATASET_ID = 7  # on showcase, 103 on dev
ACCESS_TOKEN = "2932aa73-a957-452f-975b-d62fdda2abf5"


class Tender(pydantic.BaseModel):
    detail_page: str
    title: str
    publisher: str | None
    published: datetime.datetime | None
    deadline: datetime.datetime | None
    cpv_codes: list[str] | None = None
    location: str | None = None
    award_type: str | None = None
    award_procedure: str | None = None
    scope: str | None = None
    requested_service_or_product: str | None = None
    description: str | None = None
    links: dict[str, dict[str, str]] | None = None
    external_detail_page: str | None = None
    external_detail_page_domain: str | None = None
    external_pdf: str | None = None

    def __str__(self):
        return f"{self.title} ({self.publisher})"


def scrape_service_bund_portal(max_results: int = 200):
    results_per_page = 100
    total = 0
    url = (
        f"{base_url}Content/DE/Ausschreibungen/Suche/Formular.html?view=processForm&resultsPerPage={results_per_page}"
    )

    while total < max_results and url:
        html_text = requests.get(url).text
        soup = BeautifulSoup(html_text, "html.parser")
        results_on_this_page = extract_results_from_page(soup)
        pks = [result.detail_page for result in results_on_this_page]
        pk_exists = check_pk_existence(DATASET_ID, pks, ACCESS_TOKEN)["pk_exists"]
        new_results = []
        for result in tqdm(results_on_this_page):
            total += 1
            if pk_exists.get(result.detail_page):
                # print(f"Skipping {result} because it already exists")
                continue
            try:
                add_details(result)
            except Exception as e:
                print(f"Error adding details to {result}: {e}")
                # print stack trace
                import traceback

                traceback.print_exc()
            new_results.append(result)
            if total >= max_results:
                break
            time.sleep(random.uniform(0.1, 0.2))

        if new_results:
            insert_many(DATASET_ID, [json.loads(result.model_dump_json(by_alias=True)) for result in new_results])

        print(f"Scraped {len(new_results)} new results")
        if not new_results:
            print("No new results found, stopping")
            break

        next_button = soup.find("li", class_="next").find("a")
        url = base_url + next_button["href"] if next_button else None
        print(f"Total: {total} / {max_results}")
        time.sleep(random.uniform(0.5, 1.5))

    print(f"Scraped a total of {total} results")


def extract_results_from_page(soup: BeautifulSoup) -> list[Tender]:
    results = []
    result_list = soup.find("ul", class_="result-list")
    for item in result_list.find_all("li"):
        detail_page = item.find("a")["href"].split("?")[0]
        # it might look like this with a session id at the end: IMPORTE/Ausschreibungen/eVergabe/731407.html;jsessionid=9573B3A8327CFCAC6724A0F152FEFEB6.internet622
        # strip the session id:
        detail_page = detail_page.split(".html")[0] + ".html"
        title = item.find("a")["title"].replace("Zur Ausschreibung '", "").strip("'")
        publisher = item.find("a").find("p").get_text(strip=True).replace("Vergabestelle", "").strip()
        published = (
            item.find("div", attrs={"aria-labelledby": "date"})
            .find("p")
            .get_text(strip=True)
            .replace("Veröffentlicht", "")
            .strip()
        )
        deadline = (
            item.find("div", attrs={"aria-labelledby": "location"})
            .find("p")
            .get_text(strip=True)
            .replace("Angebotsfrist", "")
            .strip()
        )
        published = convert_german_date_safe(published)
        deadline = convert_german_date_safe(deadline)
        tender = Tender(
            detail_page=detail_page,
            title=title,
            publisher=publisher,
            published=published,
            deadline=deadline,
        )
        results.append(tender)
    return results


def convert_german_date_safe(date_str):
    try:
        return datetime.datetime.strptime(date_str, "%d.%m.%y")
    except ValueError:
        return None


def add_details(tender: Tender) -> Tender:
    detail_page = tender.detail_page
    response = requests.get(base_url + detail_page)
    response.raise_for_status()
    html_text = response.text
    try:
        soup = BeautifulSoup(html_text, "html.parser")
        article = soup.find("article")
        # <p class="arbeitgeber">Vergabestelle: Landkreis Rotenburg (Wümme) </p>
        if article.find("p", class_="arbeitgeber"):
            tender.publisher = (
                article.find("p", class_="arbeitgeber").get_text(strip=True).replace("Vergabestelle: ", "")
            )

        # "Kurzinfos"
        shortlist_section = soup.find("section", class_="shortlist")
        shortlist_info = {}
        for dt, dd in zip(shortlist_section.find_all("dt"), shortlist_section.find_all("dd")):
            key = dt.get_text(strip=True)
            value = dd.get_text(strip=True)
            shortlist_info[key] = value
        if shortlist_info.get("CPV-Codes", None):
            tender.cpv_codes = map(str.strip, shortlist_info.get("CPV-Codes", None).split(","))
        if shortlist_info.get("CPV-Code", None):
            tender.cpv_codes = [shortlist_info.get("CPV-Code", None).strip()]
        if shortlist_info.get("Erfüllungsort"):
            tender.location = shortlist_info.get("Erfüllungsort").replace("Karte anschauen", "").strip()
            if "CPV-Code" in tender.location:
                tender.location = tender.location.split("CPV-Code")[0].strip()
        if shortlist_info.get("Vergabeart"):
            tender.award_type = shortlist_info.get("Vergabeart")
        if shortlist_info.get("Vergabeverfahren"):
            tender.award_procedure = shortlist_info.get("Vergabeverfahren")
        if shortlist_info.get("Leistungen und Erzeugnisse"):
            # Leistungsgegenstandt, Subject of Performance
            tender.requested_service_or_product = shortlist_info.get("Leistungen und Erzeugnisse")
        if shortlist_info.get("Ausschreibungsweite"):
            tender.scope = shortlist_info.get("Ausschreibungsweite")
        # <div class="text"><div><p>other text</p><p>...</p></div><p>Description</p><p>Description2</p></div>
        # use only direct <p> children, not nested ones
        description_parts = article.find("div", class_="text").find_all("p", recursive=False)
        if description_parts:
            tender.description = "\n".join(p.get_text(strip=True) for p in description_parts)
        description_as_pre = article.find("div", class_="text").find("pre")
        if description_as_pre:
            tender.description = description_as_pre.get_text(strip=True)

        linklist_div = soup.find("div", class_="linklist")
        linklist_info = {}
        for li in linklist_div.find_all("li"):
            a_tag = li.find("a")
            link_title = a_tag.get_text(strip=True)
            linklist_info[link_title] = {"href": a_tag["href"], "description": a_tag["title"]}
        tender.links = linklist_info
        tender.external_detail_page = linklist_info.get("Bekanntmachung (HTML-Seite)", {}).get("href", None)
        if tender.external_detail_page:
            try:
                tender.external_detail_page_domain = tender.external_detail_page.split("/")[2]
            except IndexError:
                pass
        tender.external_pdf = linklist_info.get("Bekanntmachung (PDF-Dokument)", {}).get("href", None)
    except Exception as e:
        print(f"Error parsing details for {tender}: {e}")
        print(html_text)
        # print stack trace
        import traceback

        traceback.print_exc()
    return tender


if __name__ == "__main__":
    scrape_service_bund_portal(15000)
