"""
KryxExtractor - Crawl and Export Kryx's DnD 5e website
### v0.0.2 (07/01/2019)
* Adds image downloading/encoding
* Speeds up CSS stylization by avoiding redundant tags
* Decreased waiting intervals

### v0.0.1 (06/30/2019)
* Written for Python 3
* Compiles to PDF from HTML pages
* Uses Selenium with Firefox as principle driver
* Omit Beastiary by default
* Downloads CSS to attempt CSS formatting, but only some tags, and in a naive way

## TODO
* Current version does not fix broken internal links from source HTML
* Current version does not allow for other selenium webdrivers
* Current version does not support partial crawling (e.g. just the bestiary)
* CSS multiclasses etc, are currently not supported, so certain CSS tags do not work
* Create Table of Contents and Title Page
* More beautification to fit in an 8.5x11 page more evenly
"""
import os
import re
import glob
import time
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

# Default Parameters
# URL Formatting Parameters
DEFAULT_START_URL = 'https://marklenser.com/5e'             # URL to start crawling from
DEFAULT_URL_PREFIX = 'https://marklenser.com'               # URL prefix to replace in target URLs
DEFAULT_URL_REPLACER = 'KRYX'                               # String to replace URL prefix
DEFAULT_CHANGELOG_URL = 'https://marklenser.com/changelog'  # URL of the changelog
DEFAULT_URL_SEP_CHAR = '/'                                  # Character separating URLs
# Waiting Intervals, set higher to avoid overloading target
DEFAULT_JS_WAIT_INTERVAL = 0.5                              # Interval to wait for javascript actions to occur
DEFAULT_PAGE_WAIT_INTERVAL = 0.5                              # Interval to wait between crawling pages
# Button clicking parameters
DEFAULT_CLICK_OFFSET = -5                                   # Offset for clicking off of javascript elements
DEFAULT_HIT_BUTTONS = None                                  # List of button IDs which have already been hit
DEFAULT_BUTTON_SEEK_PARAMS = ['a', {'role': 'menuitem'}]    # Parameters for finding clickable buttons
# Crawling parameters
DEFAULT_IGNORE_URLS = [                                     # URLS which should not be exported or crawled further
    'https://www.patreon.com/marklenser',
    'https://bitbucket.org/mlenser/tabletop-homebrew/issues',
    '/5e',
    '/5e/changelog',
    '/changelog',
    'https//docs.google.com/spreadsheets/d/17ZeFuwQVvb9DsMseUU8Pb0KxDU7sizhmebp-U7FuzLY/edit#gid=1095279036',
    'https://marklenser.com/5e/character/5e/playing/abilities',
    'https://marklenser.com/5e/character/5e/playing/background',
    '/5e/monsters',
    '/5e/themes/spells/all',
    '/5e/themes/maneuvers/all',
    '/5e/themes/distribution',
    '/5e/converters/pathfinder-to-5e',
    '/5e/converters/we-be-goblins-to-5e'
]
DEFAULT_HISTORY = None                                      # List of URLS already crawled
DEFAULT_STACK = None                                        # Stack data structure of URLs to crawls
DEFAULT_SELENIUM_DRIVER = None                              # Selenium Webdriver to use
DEFAULT_HTML_REMOVE_TAGS = ['header', 'footer']                         # Tags to remove from HTML
# Output parameters
DEFAULT_EXPORT_DIR = '.'                                    # Base directory to export in (overwritten if path is specified)
DEFAULT_PATH = None                                         # Path to export the intermediate PDFs and compiled PDFs
DEFAULT_VERSION = None                                      # Version string to use
DEFAULT_OUTPUT_FILENAME = None                              # Final filename to use for output
DEFAULT_CSS_FILE = ['/static/css/8.d54bb455.chunk.css']
# Other parameters
DEFAULT_VERBOSE = KryxLogger.LOG_VDEBUG                                         # Verbose console output
DEFAULT_KEEP_HTML = True
DEFAULT_HTML_SUBDIR = 'html'
DEFAULT_PDF_SUBDIR = 'pdf'
DEFAULT_KEEP_PDFS = True
DEFAULT_STORED_CSS = None


HTML_TAGS = []
with open("HTML_TAGS.txt", "r") as file:
    for line in file:
        HTML_TAGS.append(line.strip())
CSS_SELECTORS = []
with open("CSS_SELECTORS.txt", "r") as file:
    for line in file:
        CSS_SELECTORS.append(line.strip())


class KryxEtractor:
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
                 url_prefix=DEFAULT_URL_PREFIX,
                 url_replacer=DEFAULT_URL_REPLACER,
                 changelog_url=DEFAULT_CHANGELOG_URL,
                 url_sep_char=DEFAULT_URL_SEP_CHAR,
                 js_wait_interval=DEFAULT_JS_WAIT_INTERVAL,
                 page_wait_interval=DEFAULT_PAGE_WAIT_INTERVAL,
                 click_offset=DEFAULT_CLICK_OFFSET,
                 hit_buttons=DEFAULT_HIT_BUTTONS,
                 button_seek_params=DEFAULT_BUTTON_SEEK_PARAMS,
                 selenium_driver=DEFAULT_SELENIUM_DRIVER,
                 ignore_urls=DEFAULT_IGNORE_URLS,
                 keep_html=DEFAULT_KEEP_HTML,
                 keep_pdfs=DEFAULT_KEEP_PDFS,
                 html_subdir=DEFAULT_HTML_SUBDIR,
                 pdf_subdir=DEFAULT_PDF_SUBDIR,
                 stack=DEFAULT_STACK,
                 history=DEFAULT_HISTORY,
                 export_dir=DEFAULT_EXPORT_DIR,
                 version=DEFAULT_VERSION,
                 path=DEFAULT_PATH,
                 output_filename=DEFAULT_OUTPUT_FILENAME,
                 verbose=DEFAULT_VERBOSE,
                 html_remove_tags=DEFAULT_HTML_REMOVE_TAGS,
                 css_file=DEFAULT_CSS_FILE,
                 stored_css=None,
                 start_selenium=True,
                 ):
        self.start_url = start_url
        self.selenium_driver = selenium_driver
        self.start_selenium = start_selenium
        self._init_webdriver()
        self.ignore_urls = ignore_urls
        self.js_wait_interval = js_wait_interval
        self.page_wait_interval = page_wait_interval
        self.url_replacer = url_replacer
        self.export_dir = export_dir
        self.version = version
        self.click_offset = click_offset
        self.button_seek_params = button_seek_params
        self.verbose = int(verbose)
        self.changelog_url = changelog_url
        self.url_sep_char = url_sep_char
        self.url_prefix = url_prefix
        if self.version is None:
            self.version = self.get_latest_version()
        self.path = path
        self.html_subdir = html_subdir
        self.pdf_subdir = pdf_subdir
        self._init_paths()
        self.logfile = os.path.join(self.path, "KryxExtractor.log")
        self.logger = self._init_logger()
        self.hit_buttons = hit_buttons
        if self.hit_buttons is None:
            self.hit_buttons = []
        self.history = history
        if self.history is None:
            self.history = []
        self.stack = stack
        if self.stack is None:
            self.stack = []
        self.keep_html = keep_html
        self.keep_pdfs = keep_pdfs
        self.html_remove_tags = html_remove_tags
        self.output_filename = output_filename
        if self.output_filename is None:
            self.output_filename = "%s_v%s_compiled.pdf" % (self.url_replacer, self.version)
        self.css_file = css_file
        self.stored_css = stored_css
        if self.stored_css is None or not type(self.stored_css) is dict:
            self.stored_css = dict()
        self._print_own_fields()
        self._init_check_types()

    def _init_webdriver(self):
        if not self.start_selenium:
            return
        if self.selenium_driver is None:
            self.selenium_driver = webdriver.Firefox()
        try:
            self.selenium_driver.get(self.start_url)
        except selenium.common.exceptions.InvalidSessionIdException:
            self.selenium_driver = webdriver.Firefox()
        except urllib3.exceptions.MaxRetryError:
            self.selenium_driver = webdriver.Firefox()
        except selenium.common.exceptions.WebDriverException:
            self.selenium_driver = webdriver.Firefox()

        # self.selenium_driver.maximize_window()
        self.selenium_driver.set_window_position(0, 0)
        self.selenium_driver.set_window_size(850, 1100)

    def _init_check_types(self):
        """Check all field types upon intialization.
            Args: None
            Kwargs: None
            Output: None
            Fields: All fields from the object
        """
        self._assert_type(self.start_url, str, 'self.start_url')
        self._assert_type(self.selenium_driver, [webdriver.Firefox, type(None)], 'self.selenium_driver')
        self._assert_type(self.ignore_urls, list, 'self.ignore_urls')
        self._assert_type(self.js_wait_interval, [int, float], 'self.js_wait_interval')
        self._assert_type(self.page_wait_interval, [int, float], 'self.page_wait_interval')
        self._assert_type(self.url_replacer, str, 'self.url_replacer')
        self._assert_type(self.export_dir, str, 'self.export_dir')
        self._assert_type(self.path, str, 'self.path')
        self._assert_type(self.version, str, 'self.version')
        self._assert_type(self.hit_buttons, list, 'self.hit_buttons')
        self._assert_type(self.history, list, 'self.history')
        self._assert_type(self.stack, list, 'self.stack')
        self._assert_type(self.click_offset, int, 'self.click_offset')
        self._assert_type(self.button_seek_params, list, 'self.button_seek_params')
        self._assert_type(self.verbose, [int, bool], 'self.verbose')
        self._assert_type(self.changelog_url, str, 'self.changelog_url')
        self._assert_type(self.url_sep_char, str, 'self.url_sep_char')
        self._assert_type(self.url_prefix, str, 'self.url_prefix')
        self._assert_type(self.html_remove_tags, list, 'self.html_remove_tags')

    def _assert_type(self, variable, desired_type, name=None):
        """Assert a variable has a particular type.
            Args: variable (?) - a variable to assert the type of
                  desired type (type, list[type]) - the type or types of the variable to assert
            Kwargs: name - the name of the variable for error output clarity
            Fields: None
            Output: None
            External State: if the variable's actual and expected state match, no change
                            else, throws an assertion error and prints a message
        """
        if name is None:
            name = "Unknown"
        if type(desired_type) is list:
            assert type(variable) in desired_type, "TYPE ERROR FOR %s VARIABLE. REQUIRED TYPE IS %s" % (name, desired_type)
        else:
            assert type(variable) is desired_type, "TYPE ERROR FOR %s VARIABLE. REQUIRED TYPE IS %s" % (name, desired_type)

    def _init_paths(self):
        """Initialize the extraction paths. i.e. create them if they don't exist
            Args: None
            Kwargs: None
            Fields: logger, path, html_subdir, pdf_subdir, url_replace, version
            Output: None
            External State: path, html_subdir, and pdf_subdir exist if they did not exist before
        """
        if self.path is None:
            self.path = os.path.join(self.export_dir, '%s_v%s' % (self.url_replacer, self.version))
        os.makedirs(self.path, exist_ok=True)
        os.makedirs(os.path.join(self.path, self.html_subdir), exist_ok=True)
        os.makedirs(os.path.join(self.path, self.html_subdir, 'static', 'css'), exist_ok=True)
        os.makedirs(os.path.join(self.path, self.pdf_subdir), exist_ok=True)

    def _init_logger(self):
        """Initialize Logger with a file and stream handler.
                If the logger exists, remove all its handlers.

            Args: None
            Kwargs: None
            Fields: verbose (sets the logger level), logfile
            Output: logger
                Python logger object with custom levels
                    LOG_BASIC = 0       -       standard logging
                    LOG_VERBOSE = 1     -       verbose logging
                    LOG_VVERBOSE = 2    -       very verbose logging
                    LOG_VVVERBOSE = 3   -       very, very verbose logging
                    LOG_DEBUG = 4       -       debug logging
                    LOG_PARAMS = 5      -       parameter print logging
            External State: logfile named KryxExtractor exists in logfile path
        """
        logger = logging.getLogger("KryxExtractor")
        logger.setLevel(self.verbose)
        fh = logging.FileHandler(self.logfile)
        fh.setLevel(self.verbose)
        ch = logging.StreamHandler()
        ch.setLevel(self.verbose)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        logger.handlers = []    # Purge all previous handlers
        logger.addHandler(fh)
        logger.addHandler(ch)
        return logger

    def _print_own_fields(self):
        """Prints all of the KryxExtractor's fields, only at the highest log level.
            Args: None
            Kwargs: None
            Fields: logger (for printing), all other fields
            Output: None
            External State: all fields printed to logger if logger is set to PARAMS level
        """
        self.logger.vparams("PARAMETERS FOR CRAWLER\n\t\tNAME\tTYPE\tVALUE")
        for k, v in self.__dict__.items():
            self.logger.vparams('\t\t%s\t%s\t%s' % (k, type(v), str(v)))

    def clean_html(self,
                   html_source,
                   ):
        """Clean input html by removing tags.
            Args: html_source  (str)    -   string of html source
            Kwargs: None
            Fields: html_remove_tags (contains tags which will be cleaned)
            Output: cleaned, html output after desired tags have been removed
            External State: No change
        """
        self.logger.vvverbose("Cleaning HTML...")
        soup = BeautifulSoup(html_source, 'html.parser')
        for tag in self.html_remove_tags:
            if hasattr(soup, tag):
                try:
                    getattr(soup, tag).decompose()
                except AttributeError:
                    pass
        self.logger.vvverbose("Downloading images...")
        self._download_images(soup)
        self.logger.vvverbose("Grabbing CSS...")
        self._hack_css(soup)
        raw = str(soup)
        return raw

    def _hack_css(self, soup):
        """Kryx does a lot of CSS rendering inline, so we need to use selenium to
            grab the CSS elements, and hack them into the HTML. To preserve runtime,
            we only do this once per element or class, assuming they do not change
            much between pages. Desired HTML tags are loaded from HTML_TAGS.txt
            and CSS selectors are loaded from CSS_SELECTORS.txt.

            We use only some CSS selectors because the actual computed selectors
            may not translate well to a PDF. E.g. taking the fixed width and height
            selectors is generally not a good idea. 
        """
        [s.extract() for s in soup('script')]
        style_tag = soup.new_tag('style', type='text/css')
        elemform = "%s { %s } "
        internalform = "%s: %s; "
        classes = []
        for element in soup.find_all(class_=True):
            classes.extend(element["class"])
        for tag in HTML_TAGS:
            if tag in self.stored_css.keys():
                style_tag.append(self.stored_css[tag])
                continue
            try:
                tagelem = self.selenium_driver.find_element_by_tag_name(tag)
            except selenium.common.exceptions.NoSuchElementException:
                continue
            properties = self.selenium_driver.execute_script('return window.getComputedStyle(arguments[0], null);', tagelem)
            internaltext = ""
            for property in properties:
                if property in CSS_SELECTORS:
                    value = tagelem.value_of_css_property(property)
                    if len(value) > 0:
                        internaltext += internalform % (property, value)
            style_tag.append(elemform % (tag, internaltext))
            self.stored_css[tag] = elemform % ('.'+tag, internaltext)
        # TODO - consolidate this code
        for tag in classes:
            if tag in self.stored_css.keys():
                style_tag.append(self.stored_css[tag])
                continue
            try:
                tagelem = self.selenium_driver.find_element_by_class_name(tag)
            except selenium.common.exceptions.NoSuchElementException:
                continue
            properties = self.selenium_driver.execute_script('return window.getComputedStyle(arguments[0], null);', tagelem)
            internaltext = ""
            for property in properties:
                if property in CSS_SELECTORS:
                    value = tagelem.value_of_css_property(property)
                    if len(value) > 0:
                        internaltext += internalform % (property, value)
            style_tag.append(elemform % ('.'+tag, internaltext))
            self.stored_css[tag] = elemform % ('.'+tag, internaltext)
        soup.head.append(style_tag)

    def _resolve_static_path(self, src):
        destination_path = os.path.normpath('/'.join([os.path.abspath(self.path), self.html_subdir, src])).replace('\\', '/')
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        return destination_path

    def _resolve_image_base64(self, path):
        with open(path, 'rb') as file:
            encoding = base64.b64encode(file.read())
            url = "data:image/png;base64, %s" % (encoding.decode())
        return url

    def _download_images(self, soup):
        images = soup.findAll('img')
        for image in images:
            src = image.get('src')
            if 'data:' in src:
                continue
            if 'http' in src:
                url = src
                src = 'static/media/%s' % url.rsplit('/', 1)[-1]
            else:
                url = "%s%s" % (self.url_prefix, src)
            destination_path = self._resolve_static_path(src)
            urllib.request.urlretrieve(url, destination_path)
            image_data = self._resolve_image_base64(destination_path)
            self.logger.vvdebug("Retrieved file %s from url %s to path %s" % (src, url, destination_path))
            image['src'] = image_data

    def get_menuitem_links(self,
                           html_source):
        """Click all menuitem buttons on a page, and update links that appear after clicking on them.

            Args: html_source (str) - source html for a page
            Kwargs: None
            Fields: selenium_driver (for navigation)
                    hit_buttons (to store which buttons have been visited)
                    button_seek_params (to find the buttons)
                    js_wait_interval (to define how long to wait after clicking)
                    click_offset (to define where to click to destroy the menus)
                    logger
            Output:
                valid_links (list[str]) - list of strings with valid link urls
            External State: no change, all buttons uncliked on webpage, and still on original URL
        """
        soup = BeautifulSoup(html_source, 'html.parser')
        clickableButtons = soup.findAll('button', {"type": "button"})
        valid_links = []
        for button in clickableButtons:
            if button.get('id') in self.hit_buttons:
                continue
            try:
                sel_button = self.selenium_driver.find_element_by_id(button.get('id'))
            except selenium.common.exceptions.NoSuchElementException:
                continue
            except Exception:
                self._init_webdriver()
                sel_button = self.selenium_driver.find_element_by_id(button.get('id'))
            self.logger.vdebug("Found button called %s" % button.get('id'))
            sel_button.click()
            time.sleep(self.js_wait_interval)
            new_source = self.selenium_driver.page_source
            new_soup = BeautifulSoup(new_source, 'html.parser')
            valid_links += list([a.get('href') for a in new_soup.find_all(*self.button_seek_params)
                                 if a.get('href') not in valid_links])
            action = webdriver.common.action_chains.ActionChains(self.selenium_driver)
            action.move_to_element_with_offset(sel_button, self.click_offset, self.click_offset)
            action.click()
            action.perform()
            time.sleep(self.js_wait_interval)
            self.hit_buttons.append(button.get('id'))
        return valid_links

    def is_valid_ref(self,
                     ref,
                     fullref=None
                     ):
        """Check if a reference URL is valid, i.e. we do not want to ignore it,
                it has not been visited already, and we're not already planning to visit it.
                Also the URL is not an in-page link, with a "#", or a reference to a different
                    external webpage.

            Args: ref (str)     - the reference url to check
            Kwargs: fullref (str) - an additional reference to check
            Fields: ignore_urls, history, stack
            Output: valid (bool) - is the URL valid
            External State: No change
        """
        valid = ref not in self.ignore_urls + self.history + self.stack
        if fullref is not None:
            valid = valid and fullref not in self.ignore_urls + self.history + self.stack
        valid = valid and 'http' not in ref
        valid = valid and '#' not in ref
        return valid

    def get_links(self, html_source):
        """Grab all unvisited links on an HTML source page.
            Args: html_source (str) - the source html
            Kwargs: None
            Fields: None
            Output: links (list[str]) - list of valid reference URLs to visit
            External State: No change, selenium driver on URL, no buttons clicked
        """
        soup = BeautifulSoup(html_source, 'html.parser')
        valid_links = self.get_menuitem_links(html_source)
        valid_links += list([a.get('href') for a in soup.find_all('a') if a.get('href') not in valid_links])
        links = []
        for ref in valid_links:
            fullref = "%s%s" % (self.url_prefix, ref)
            if self.is_valid_ref(ref, fullref=fullref):
                links.append(fullref)
        return links

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
            pdf=os.path.join(self.path, self.pdf_subdir, "page_%d_%s.pdf" % (self.history.index(url), filename_prefix)),
            html=os.path.join(self.path, self.html_subdir, "%s.html" % filename_prefix)
        )
        if filetype.lower() not in filenames.keys():
            raise ValueError("Export filetype %s is not supported" % filetype)
        return filenames.get(filetype.lower())

    def export_page_from_url(self, url):
        """Exports HTML and PDF pages from a URL.

            Args: url (str) -   the url to export from
            Kwargs: None
            Fields: logger
            Output: html_source, the final html source which is output
                    new_links, links extracted prior to cleaning
            External State: exported PDF file exists and HTML exists, selenium driver on URL
        """
        filename_pdf = self.make_output_filename(url, 'pdf')
        filename_html = self.make_output_filename(url, 'html')
        start = timeit.default_timer()
        try:
            self.selenium_driver.get(url)
        except Exception:
            self._init_webdriver()
            self.selenium_driver.get(url)
        html_source = self.selenium_driver.page_source
        self.logger.vvdebug("Took %f seconds to navigate to page" % (timeit.default_timer()-start))
        start = timeit.default_timer()
        new_links = self.get_links(html_source)
        self.logger.vvdebug("Took %f seconds to grab new links on page" % (timeit.default_timer()-start))
        start = timeit.default_timer()
        html_source = self.clean_html(html_source)
        self.logger.vvdebug("Took %f seconds clean HTML" % (timeit.default_timer()-start))
        self.logger.vvverbose("Creating HTML file %s" % filename_html)
        start = timeit.default_timer()
        with open(filename_html, 'w', encoding='utf-8') as file:
            file.write(html_source)
        self.logger.vvdebug("Took %f seconds write HTML" % (timeit.default_timer()-start))
        self.logger.vvverbose("Creating PDF file %s" % filename_pdf)
        start = timeit.default_timer()
        try:
            pdfkit.from_file(filename_html, filename_pdf)
        except OSError as ex:
            pass
        self.logger.vvdebug("Took %f seconds write PDF" % (timeit.default_timer()-start))
        return html_source, new_links

    def get_latest_version(self):
        """Get the latest version from the changelog. Assumes that the version
            is the only string on the page which uses the h1 tag. This is based
            on how Kryx designed the site as of 6/29/2019.

            Args: None
            Kwargs: None
            Fields: changelog_url, selenium_driver, version
            Output: version, the latest version which is found
            External State: selenium driver on changelog page
        """
        if not self.start_selenium:
            return "0"
        self.selenium_driver.get(self.changelog_url)
        html_source = self.selenium_driver.page_source
        soup = BeautifulSoup(html_source, 'html.parser')
        versions = soup.findAll("h1", {"class": "sc-gzVnrw feaeiA"})
        version = versions[0].getText()
        return version

    def init_site_settings(self):
        """Initialize settings on the site. Since selenium spawns a new window
            the settings are automatically set to use the metric system (as of 06/29/2019).
            So we click that button once to turn off the metric system.

            Args: None
            Kwargs: None
            Fields: selenium_driver, js_wait_interval
            Output: None
            External State: Metric System off on selenium-driven webpage
        """
        sel_button = self.selenium_driver.find_element_by_id('settings')
        self.logger.vvverbose("Clicking on settings button...")
        sel_button.click()
        time.sleep(self.js_wait_interval)
        self.selenium_driver.find_elements_by_xpath("//*[contains(text(), 'Metric')]")[1].click()
        time.sleep(self.js_wait_interval)
        action = webdriver.common.action_chains.ActionChains(self.selenium_driver)
        action.move_to_element_with_offset(sel_button, 5, 5)
        self.logger.vvverbose("Turning off metric system...")
        action.click()
        action.perform()
        time.sleep(self.js_wait_interval)

    def _retrieve_css(self):
        for src in self.css_file:
            #filename = url.rsplit('/', 1)[-1]
            url = "%s%s" % (self.url_prefix, src)
            filepath = self._resolve_static_path(src)
            urllib.request.urlretrieve(url, filepath)
            self.logger.vvverbose("Retrieved file %s from url %s to path %s" % (src, url, filepath))

    def crawl(self):
        """This function controls all of the actual crawling which is done. Start from the
            starting url, find all of the links available on that first page, and follow them
            using a depth-first search. A stack is maintained to perform the DFS and to track the
            history of the search. This means that the output PDF is organized by following the links
            in the order they are found on the site, and in the order they appear on each subsequent page.

            Order of crawling operations:
                1. Initialize Site settings (turn metric system off)
                2. Append the start URL to the stack and history
                3. Begin the crawling loop
                4. While there are URLs in the stack to visit, visit top URL on stack, append it to history
                5. Export the page after cleaning to HTML and PDF format
                6. Find all valid links on the page which aren't already in the stack, history, or ignore list
                7. Pop the current URL off the stack
                8. Push all valid links found to the stack (if any)
                9. Sleep to avoid overloading the site, and iterate

            Args: None
            Kwargs: None
            Fields: start_url, stack, history, logger, page_wait_interval
            Output: None
            External State: if keep_html, all html files and subdir deleted. otherwise, html pages exist in html_subdir
                            pdf pages exist in html_subdir
        """
        self._init_paths()  # init paths again, just in case they've been cleaned up
        self._retrieve_css()
        try:
            self.init_site_settings()
        except Exception:
            self._init_webdriver()
            self.init_site_settings()
        self.stack.append(self.start_url)
        starttime = timeit.default_timer()
        self.logger.basic("Starting to crawl at %s" % self.start_url)
        while len(self.stack) > 0:
            crawlstart = timeit.default_timer()
            url = self.stack[0]
            self.history.append(url)
            self.logger.verbose(("Exporting URL %s at page %s" % (url, self.history.index(url))))
            source, new_links = self.export_page_from_url(url)

            self.logger.vvdebug("Found links: %s" % (str(new_links)))
            self.stack.remove(url)
            self.stack = new_links + self.stack
            self.logger.vdebug(("%d pages now left in stack..." % len(self.stack)))
            crawlend = timeit.default_timer()
            self.logger.verbose("Exported URL %s in %f seconds" % (url, crawlend-crawlstart))
            self.logger.vverbose("sleeping for %f seconds..." % (self.page_wait_interval))
            time.sleep(self.page_wait_interval)
        endtime = timeit.default_timer()
        self.logger.basic("Finished crawling. Took %f seconds" % (endtime-starttime))
        self._crawl_cleanup()

    def _crawl_cleanup(self):
        if not self.keep_html:
            os.rmdir(os.path.join(self.path, self.html_subdir))
        try:
            self.selenium_driver.close()
        except selenium.common.exceptions.WebDriverException:
            pass

    def pdf_cat(self, input_files, output_stream):
        """
            Concatenate a list of PDF files to a file output stream.

            Args: input_files (list[str]) - list of pdf input files
                   output_stream (python file stream) - python file stream
            Kwargs: None
            Fields: None
            Output: None
            External State: output stream has created compiled pdf
        """
        input_streams = []
        try:
            for input_file in input_files:
                input_streams.append(open(input_file, 'rb'))
            writer = PdfFileWriter()
            for reader in map(PdfFileReader, input_streams):
                for n in range(reader.getNumPages()):
                    writer.addPage(reader.getPage(n))
            writer.write(output_stream)
        finally:
            for f in input_streams:
                f.close()

    def export_final_pdf(self):
        """Export the final compiled PDF.
            Args: None
            Kwargs: None
            Fields: logger, output_filename
            Output: None
            External State: logger exists, pdf subdir is removed, final pdf is created
        """
        self.logger.basic("Exporting pdf...")
        pdfs = [self.make_output_filename(url, 'pdf') for url in self.history]
        self.logger.verbose(("Found %d pages..." % len(pdfs)))
        output_path = os.path.join(self.path, self.output_filename)
        self.logger.verbose("Outputting to path %s..." % output_path)
        start = timeit.default_timer()
        self.pdf_cat(pdfs, open(output_path, 'wb'))
        self.logger.vvdebug("Took %f seconds to compiled PDF" % (timeit.default_timer()-start))
        self._export_cleanup()

    def _export_cleanup(self):
        """cleanup function for exporting
            Args: None
            Kwargs: None
            Fields: None
            Output: None
            External State: pdf subdir is removed
        """
        if not self.keep_pdfs:
            if os.path.exists(self.pdf_subdir):
                os.rmdir(self.pdf_subdir)

    def _webdriver_cleanup(self):
        """shut down the webdriver
            Args: None
            Kwargs: None
            Fields: None
            Output: None
            External State: Webdriver shutdown
        """
        try:
            self.selenium_driver.close()
        except selenium.common.exceptions.WebDriverException:
            pass
        try:
            self.selenium_driver.quit()
        except selenium.common.exceptions.WebDriverException:
            pass

    def cleanup(self):
        """Do all cleanup operations
            Args: None
            Kwargs: None
            Fields: None
            Output: None
            External State: html and pdf subdir are removed, webdriver is shut down
        """
        self._crawl_cleanup()
        self._export_cleanup()
        self._webdriver_cleanup()

    def run(self):
        self.crawl()
        self.export_final_pdf()
        self.cleanup()


if __name__ == '__main__':
    extractor = KryxEtractor()
    extractor.run()
