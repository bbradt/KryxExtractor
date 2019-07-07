"""
KryxExtractor - Crawl and Export Kryx's DnD 5e website
# v0.0.2 (07/01/2019)
* Adds image downloading/encoding
* Speeds up CSS stylization by avoiding redundant tags
* Decreased waiting intervals

# v0.0.1 (06/30/2019)
* Written for Python 3
* Compiles to PDF from HTML pages
* Uses Selenium with Firefox as principle driver
* Omit Beastiary by default
* Downloads CSS to attempt CSS formatting, but only some tags, and in a naive way

# TODO
* Current version does not fix broken internal links from source HTML
* Current version does not allow for other selenium webdrivers
* Current version does not support partial crawling (e.g. just the bestiary)
* CSS multiclasses etc, are currently not supported, so certain CSS tags do not work
* Create Table of Contents and Title Page
* More beautification to fit in an 8.5x11 page more evenly
"""
import itertools
import os
import re
import utils
import glob
import time
import pandas
import timeit
import base64
import pdfkit
import logging
import selenium
import urllib.request
import urllib3
from bs4 import BeautifulSoup
from selenium import webdriver
from PyPDF2 import PdfFileWriter, PdfFileReader
import KryxLogger
import KryxExtractor

DEFAULT_CSV_SUBDIR = "csv"
DEFAULT_START_URL = "https://marklenser.com/5e/themes/spells/all"
DEFAULT_COLUMN_ORDER = ["name", "power_sources", "theme", "mana", "cast time", "concentration", "ritual"]
DEFAULT_DEST_COLUMNS = ["name", "description", "mana", "ritual", "cast_time", "concentration",
                        "range", "duration", "target", "save", "effect", "augmentation", "damage"]
DEFAULT_URL_REPLACE = "KRYX_SPELLS"


class KryxSpellExtractor(KryxExtractor.KryxEtractor):
    """KryxExtractor
            Scrapes Kryx's website for his current version of Homebrew.
            Pulls down all available pages unless specified to ignore them, and compiles
            them into a single PDF.

            Args:
                None
            Kwargs:
                | **NAME**            |   **TYPE**        |   **DESCRIPTION** |
                | -------------------- |:-----------------------:| -------------------:|
                | start_url           |   str                 |   URL to start crawling from |
                | url_prefix          |   str                 |   URL prefix to replace in target URLs |
                | url_replace         |   str                 |   String to replace URL prefix |
                | changelog_url       |   str                 |   URL of the changelog |
                | url_sep_char        |   str                 |   Separating character in URLs |
                | js_wait_interval    |   int,float           |   Interval to wait for javascript actions to occur |
                | page_wait_interval  |   int,float           |   Interval to wait between crawling pages |
                | click_offset        |   int                 |   Offset for clicking off of javascript elements |
                | hit_buttons         |   list[str]           |   List of button IDs which have already been hit |
                | button_seek_params  |   list[args]          |   Parameters for finding clickable buttons |
                | selenium_driver     |   Firefox Webdriver   |   Selenium Webdriver to use |
                | ignore_urls         |   list[str]           |   URLS which should not be exported or crawled further |
                | stack               |   list[str]           |   Stack data structure of URLs to crawls |
                | history             |   list[str]           |   List of URLS already crawled |
                | html_remove_tags    |   list[str]           |   Tags to remove from HTML |
                | export_dir          |   str                 |   Base directory to export in (irrelevent if path is specified) |
                | version             |   str                 |   Path to export the intermediate PDFs and compiled PDFs |
                | path                |   str                 |   Version string to use |
                | output_filename     |   str                 |   Final filename to use for output |
                | verbose             |   int                 |   Verbose console output |
                | css_file            |   str                 | static url of CSS file to download |
                | stored_css          |   dict[str:str]       | stored CSS for tags and classes |
    """

    def __init__(self,
                 start_url=DEFAULT_START_URL,
                 csv_subdir=DEFAULT_CSV_SUBDIR,
                 column_order=DEFAULT_COLUMN_ORDER,
                 dest_columns=DEFAULT_DEST_COLUMNS,
                 url_replacer=DEFAULT_URL_REPLACE,
                 **kwargs
                 ):
        self.csv_subdir = csv_subdir
        self.column_order = column_order
        self.dest_columns = dest_columns
        super(KryxSpellExtractor, self).__init__(start_url=start_url, url_replacer=url_replacer, **kwargs)

    def _init_paths(self):
        """Initialize the extraction paths. i.e. create them if they don't exist
            Args: None
            Kwargs: None
            Fields: logger, path, html_subdir, pdf_subdir, url_replace, version
            Output: None
            External State: path, html_subdir, and pdf_subdir exist if they did not exist before
        """
        super(KryxSpellExtractor, self)._init_paths()
        os.makedirs(os.path.join(self.path, self.csv_subdir), exist_ok=True)

    def grab_table(self, html_source):
        self.expand_tables()
        html_source = self.selenium_driver.page_source
        soup = BeautifulSoup(html_source)
        table = soup.find('table')
        tbody = table.find('tbody')
        trs = tbody.find_all('tr', recursive=False)
        df = []
        row = dict()
        for i, tr in enumerate(trs):
            tds = tr.find_all('td')
            if i % 2 == 0:
                row = dict()
                for j, td in enumerate(tds):
                    if j >= len(self.column_order):
                        continue
                    key = self.column_order[j]
                    row[key] = td.text
                    if key == 'concentration':
                        row[key] = row[key].lower().strip() == 'concentration'
                    if key == 'ritual':
                        row[key] = row[key].lower().strip() == 'ritual'
                    if key == 'power_sources':
                        row[key] = row[key].replace(',', ';')
            else:
                row['description'] = str(tr)
                for rkey in self.dest_columns:
                    if rkey not in row.keys():
                        row[rkey] = None
                df.append(row)
        return pandas.DataFrame(df)

    def expand_tables(self):
        buttons = self.selenium_driver.find_elements_by_xpath("//button[@aria-label='Show more']")[1:]
        for button in buttons:
            button.click()
            time.sleep(self.js_wait_interval)

    def export_page_from_url(self, url):
        """Exports HTML and PDF pages from a URL.

            Args: url (str) -   the url to export from
            Kwargs: None
            Fields: logger
            Output: html_source, the final html source which is output
                    new_links, links extracted prior to cleaning
            External State: exported PDF file exists and HTML exists, selenium driver on URL
        """
        filename_csv = self.make_output_filename(url, 'csv')
        start = timeit.default_timer()
        try:
            self.selenium_driver.get(url)
        except Exception:
            self._init_webdriver()
            self.selenium_driver.get(url)
        html_source = self.selenium_driver.page_source
        self.logger.vvdebug("Took %f seconds to navigate to page" % (timeit.default_timer()-start))
        start = timeit.default_timer()
        table = self.grab_table(html_source)
        self.logger.vvdebug("Took %f seconds to grab table page" % (timeit.default_timer()-start))
        start = timeit.default_timer()
        with open(filename_csv, 'w', encoding='utf-8') as file:
            table.to_csv(file, sep=",", float_format='%.2f', index=False, line_terminator='\n', encoding='utf-8')
        self.logger.vvdebug("Took %f seconds write CSV" % (timeit.default_timer()-start))
        return html_source, []

    def make_output_filename(self, url, filetype):
        """Create an output filename for a given filetype.
            Filetypes supported are PDF and HTML.
            PDF files are output with a page number in front of them.
            HTML files are just output with the slugified URL.

            Args: url   (str)   - the url to convert to a filename
                  filetype (str)    - 'pdf' or 'html' the filetype to create for
            Kwargs: None
            Fields: start_url, url_replace, url_sep_char, path, history, html_subdir, pdf_subdir
            External State: No change
        """
        prefix = url.replace(self.start_url, self.url_replacer)
        filename_prefix = prefix.replace(self.url_sep_char, '_')
        filenames = dict(
            csv=os.path.join(self.path, self.csv_subdir, "%s.csv" % filename_prefix)
        )
        if filetype.lower() not in filenames.keys():
            raise ValueError("Export filetype %s is not supported" % filetype)
        return filenames.get(filetype.lower())

    def clean_csv(self,
                  csv_file="D:\\Dropbox\\BRAD\\python\\kryx_version\\KRYX_SPELLS_v13.0.0-beta-5\\csv\\KRYX_SPELLS.csv",
                  csv_out="D:\\Dropbox\\Campaigns\\falloutflorida\\backend\\media\\notes\\spells_original.csv"):
        df = pandas.read_csv(csv_file)
        df = df.where((pandas.notnull(df)), None)
        newdf = []
        for index, row in df.iterrows():
            description = row['description']
            row.pop('target')
            name = row['name']
            mana = row['mana']
            cast_time = row.pop('cast time')
            row['cast_time'] = cast_time

            if "Augment" in description:
                endtag = "</div>"
                if "</p></div>" in description:
                    endtag = "</p>" + endtag
                elif "</ul></div>" in description:
                    endtag = "</ul></div>"
                else:
                    input(("UHOH", description))
                augmentstr = description[description.index("<h5"):(description.index(endtag)+4)]
                row['augmentation'] = augmentstr
            cut_description = description.replace(augmentstr, "").replace('concentration, ', '').replace('(ritual)', '')

            damage = None
            damages = re.search(r"[1-9]d[1-9] [a-z\s].*? damage", cut_description)
            if damages is not None:
                row['damage'] = damages.group(0)
            damage = row.pop('damage')
            if damage is not None and len(damage.split()) == 3:
                dice, dtype, _ = damage.split()[:]
                dicequant, dicetype = dice.split('d')[:]
                row['damage.dice_quantity'] = dicequant
                row['damage.dice_type'] = dicetype
                row['damage.damage_type'] = dtype
            else:
                row['damage.dice_quantity'] = None
                row['damage.dice_type'] = None
                row['damage.damage_type'] = None

            ranges = re.search(r"within [1-9].*? feet", cut_description)
            if ranges is not None:
                row['range'] = ranges.group(0).replace('within ', '')
            elif "cone or line" in cut_description or "line or cone" in cut_description:
                row['range'] = "line or cone"
            elif "touch" in cut_description:
                row['range'] = "touch"
            else:
                row['range'] = 'self'

            saving_throws = re.search(r"[A-Z][a-z]*.? saving throw", cut_description)
            if saving_throws is not None:
                row['save'] = saving_throws.group(0)

            duration_regexs = [
                r"[1-9] [a-z]*.?\/mana",
                r"[1-9] hour(s|)",
                r"[1-9] minute(s|)",
                r"[1-9] mile(s|)",
                r"[1-9] round(s|)",
                r"(until|Until)[\sA-Za-z]*.? turn"
            ]
            found = False
            for duration_regex in duration_regexs:
                durations = re.search(duration_regex, cut_description)
                if durations is not None:
                    row['duration'] = durations.group(0)
                    found = True
                    break
            if not found:
                row['duration'] = 'instantaneous'
            # if 'As' in cut_description:
            #    cut_description = cut_description[cut_description.index('As'):]

            if row['augmentation'] is not None:
                clean = re.compile(r'<div.*?>')
                row['augmentation'] = re.sub(clean, '', row['augmentation'])
                clean = re.compile(r'</div.*?>')
                row['augmentation'] = re.sub(clean, '', row['augmentation'])
            clean = re.compile(r'<div.*?>')
            cut_description = re.sub(clean, '', cut_description)
            clean = re.compile(r'</div.*?>')
            cut_description = re.sub(clean, '', cut_description)
            clean = re.compile(r'(?i)<tr[^>]*>')
            cut_description = re.sub(clean, '', cut_description)
            clean = re.compile(r'(?i)</tr[^>]*>')
            cut_description = re.sub(clean, '', cut_description)
            clean = re.compile(r'(?i)<td[^>]*>')
            cut_description = re.sub(clean, '', cut_description)
            clean = re.compile(r'(?i)</td[^>]*>')
            cut_description = re.sub(clean, '', cut_description)
            clean = re.compile(r'(?i)<h4[^>]*>%s</h4>%s' % (name, mana))
            cut_description = re.sub(clean, '', cut_description)
            if row['augmentation'] is not None:
                clean = re.compile(r'<h5 class="sc-fjdhpX gtpEVG">Augment</h5>')
                row['augmentation'] = re.sub(clean, '', row['augmentation'])

            cut_description = cut_description.replace('â€™', '\'')
            row['description'] = cut_description
            row['cast_range'] = row.pop('range')
            row['spell_save'] = row.pop('save')
            row['spell_theme'] = row.pop('theme')
            newdf.append(row)
        pandas.DataFrame(newdf).to_csv(csv_out, index=False)

    def run(self):
        self.crawl()


if __name__ == '__main__':
    extractor = KryxSpellExtractor(start_selenium=False)
    # extractor.run()
    extractor.clean_csv()
