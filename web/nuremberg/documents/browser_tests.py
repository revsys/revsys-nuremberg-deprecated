from time import sleep

import pytest
from django.urls import reverse
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import (
    visibility_of_element_located,
)
from selenium.webdriver.support.ui import Select, WebDriverWait as wait

from nuremberg.core.tests.clientside_helpers import (
    at,
    element_has_attribute,
    global_variable_exists,
)
from nuremberg.core.tests.clientside_helpers import (  # noqa, pytest fixtures
    browser,
    unblocked_live_server,
)
from nuremberg.documents.models import Document


@pytest.fixture(scope='module')
def document(browser, unblocked_live_server):  # noqa
    document_id = 1
    browser.get(
        unblocked_live_server.url
        + reverse('documents:show', kwargs={'document_id': document_id})
    )
    browser.execute_script(
        "$('html').removeClass('touchevents'); "
        "$('html').removeClass('no-xhrresponsetypeblob'); "
        "Modernizr.touchevents = false; "
        "Modernizr.xhrresponsetypeblob = true;"
    )
    assert Document.objects.get(id=document_id).title in browser.title

    return browser


@pytest.fixture
def viewport(document):
    document.execute_script("$('.viewport-content').scrollTop(0);")
    return document.find_element(By.CSS_SELECTOR, '.viewport-content')


@pytest.fixture
def log():
    print('BROWSER LOG:', document.get_log('browser'))


def test_zooming(document, viewport):
    img = document.find_element(By.CSS_SELECTOR, '.document-image img')

    # scroll mode
    document.find_element(By.CSS_SELECTOR, '.tool-buttons .scroll').click()

    # image is full-width (mod scrollbars)
    document.save_screenshot('screenshots/full-size.png')
    assert img.size['width'] in range(
        viewport.size['width'] - 40, viewport.size['width']
    )

    # zoom out
    # context_click seems not to work?
    # ActionChains(document).move_to_element_with_offset(viewport, 50, 50).context_click().perform()
    document.find_element(By.CSS_SELECTOR, 'button.zoom-out').click()
    sleep(0.5)
    expected_scale = 1 / 2

    document.save_screenshot('screenshots/zoomed-out.png')
    assert int(img.size['width']) in range(
        int(viewport.size['width'] * expected_scale - 40),
        int(viewport.size['width'] * expected_scale),
    )

    # zoom in
    ActionChains(document).move_to_element(viewport).move_by_offset(
        50, 50
    ).click().perform()
    sleep(0.5)
    ActionChains(document).move_to_element(viewport).move_by_offset(
        50, 50
    ).click().perform()
    sleep(0.5)
    expected_scale = 1.5

    document.save_screenshot('screenshots/zoomed-in.png')
    assert int(img.size['width']) in range(
        int(viewport.size['width'] * expected_scale - 40),
        int(viewport.size['width'] * expected_scale),
    )


def test_page_navigation(document, viewport):
    page = document.find_element(
        By.CSS_SELECTOR, '.document-image[data-page="20"]'
    )
    offsetTop = document.execute_script("return arguments[0].offsetTop;", page)
    document.find_element(By.CSS_SELECTOR, '.page-buttons .last-page').click()
    sleep(0.1)
    document.save_screenshot('screenshots/last-page.png')
    assert int(
        document.execute_script("return arguments[0].scrollTop;", viewport)
    ) in range(int(offsetTop - 25), int(offsetTop + 25))

    page = document.find_element(
        By.CSS_SELECTOR, '.document-image[data-page="19"]'
    )
    offsetTop = document.execute_script("return arguments[0].offsetTop;", page)
    document.find_element(By.CSS_SELECTOR, '.page-buttons .prev-page').click()
    sleep(0.1)
    document.save_screenshot('screenshots/prev-page.png')
    assert int(
        document.execute_script("return arguments[0].scrollTop;", viewport)
    ) in range(offsetTop - 25, offsetTop + 25)

    page = document.find_element(
        By.CSS_SELECTOR, '.document-image[data-page="1"]'
    )
    offsetTop = document.execute_script("return arguments[0].offsetTop;", page)
    document.find_element(By.CSS_SELECTOR, '.page-buttons .first-page').click()
    sleep(0.1)
    document.save_screenshot('screenshots/first-page.png')
    assert int(
        document.execute_script("return arguments[0].scrollTop;", viewport)
    ) in range(offsetTop - 25, offsetTop + 25)

    page = document.find_element(
        By.CSS_SELECTOR, '.document-image[data-page="2"]'
    )
    offsetTop = document.execute_script("return arguments[0].offsetTop;", page)
    document.find_element(By.CSS_SELECTOR, '.page-buttons .next-page').click()
    sleep(0.1)
    document.save_screenshot('screenshots/next-page.png')
    assert int(
        document.execute_script("return arguments[0].scrollTop;", viewport)
    ) in range(offsetTop - 25, offsetTop + 25)

    page = document.find_element(
        By.CSS_SELECTOR, '.document-image[data-page="10"]'
    )
    offsetTop = document.execute_script("return arguments[0].offsetTop;", page)
    select = Select(
        document.find_element(By.CSS_SELECTOR, '.page-buttons select')
    )
    select.select_by_visible_text('Sequence No. 10')
    sleep(0.1)
    document.save_screenshot('screenshots/tenth-page.png')
    assert int(
        document.execute_script("return arguments[0].scrollTop;", viewport)
    ) in range(offsetTop - 25, offsetTop + 25)
    assert '00001010.jpg' in document.find_element(
        By.CSS_SELECTOR, '.page-buttons .download-page'
    ).get_attribute('href')


def test_pdf_generation(document):
    # extremely ugly shim to detect PDF save
    document.execute_script(
        """
        var _cENS = document.createElementNS;
        document.createElementNS = function () {
            document.createElementNS = _cENS;
            window.save_link = document.createElementNS.apply(document, arguments);
            window.save_link.dispatchEvent = function () {
                window.save_link_clicked = true;
            };
            document.body.appendChild(window.save_link);
            return window.save_link;
        }"""
    )

    document.find_element(By.CSS_SELECTOR, 'button.download-pdf').click()
    inner_save_link = wait(document, 10).until(
        global_variable_exists('save_link')
    )
    save_link = wait(document, 1).until(
        visibility_of_element_located(at('.download-options a'))
    )
    save_link.click()
    document.save_screenshot('screenshots/building-pdf.png')
    download = wait(document, 30).until(
        element_has_attribute(inner_save_link, 'download')
    )
    assert 'HLSL Nuremberg Document #1 pages 1-20.pdf' in download
