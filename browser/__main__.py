import tkinter
from typing import Annotated

from browser.browser import Browser
from browser.url import Url


def main(
    url: Annotated[str, "URL"],
):
    # browser = Browser(rtl=True)
    browser = Browser()
    browser.open(url)

    tkinter.mainloop()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="URL to open.")
    args = parser.parse_args()
    main(args.url)
