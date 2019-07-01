# KryxExtractor

This tools extracts and exports Kryx's 5e homebrew website to a PDF for posterity.

Kryx's Website is https://marklenser.com/5e

The tool crawls the website using a Depth-First search of links on the page, and 
organizes pages found in that search into a fully compiled PDF.

## Usage

Here are the usage instructions for running the tools

### Requirements

Install the requirements in requirements.txt (better to do so in a virtual environment).
    ```bash
    pip install -r requirements.txt
    ```

You will need Firefox and the Firefox geckodriver. These can be found here:

    https://github.com/mozilla/geckodriver/releases

Add the geckodriver to your $PATH. If you are running LINUX
```bash
export PATH="/path/to/geckodriver:$PATH"
```

The tool can be run using default parameters by just running the script
```bash
python KryxExtractor.py
```
or on the python command line
```python
extractor = KryxExtractor()
extractor.run()
```

which will create a PDF file of the exported website.
To cleanup PDF and HTML pages and just keep the compiled final PDF 
```python
extractor = KryxExtractor(keep_pdf=False, keep_html=False)
extractor.run()
```

# Changelog

### v0.0.1 (06/30/2019)
* Written for Python 3
* Compiles to PDF from HTML pages
* Uses Selenium with Firefox as principle driver
* Omit Beastiary by default

## TODO
* Current version does not fix broken links from source HTML
* Current version does not preserve any formatting/CSS from Kryx
* Current version does not extract images consistently
* Current version does not allow for other selenium webdrivers
* Current version does not support partial crawling (e.g. just the bestiary)

# Parameters

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
| verbose             |   int               |   Verbose console output |
