from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os

def main():
    date_input = input("Введите дату в формате YYYY-MM-DD: ").strip()
    kml_path = input("Введите полный путь к KML-файлу: ").strip()

    if not os.path.isfile(kml_path):
        print(f"Ошибка: файл '{kml_path}' не найден.")
        return

    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=options)

    try:
        driver.get("https://browser.dataspace.copernicus.eu")
        wait = WebDriverWait(driver, 20)

        try:
            date_picker = wait.until(
                EC.presence_of_element_located((By.ID, "datePicker"))
            )
            date_picker.clear()
            date_picker.send_keys(date_input)
            date_picker.send_keys(Keys.ENTER)
            print(f"Дата '{date_input}' установлена.")
        except TimeoutException:
            print("Не удалось найти элемент для ввода даты.")
            driver.quit()
            return

        time.sleep(2)

        try:
            kml_upload = wait.until(
                EC.presence_of_element_located((By.ID, "kmlUpload"))
            )
            kml_upload.send_keys(kml_path)
            print(f"KML-файл '{kml_path}' загружен.")
        except TimeoutException:
            print("Не удалось найти элемент для загрузки KML-файла.")
            driver.quit()
            return

        time.sleep(3)

        try:
            search_button = wait.until(
                EC.element_to_be_clickable((By.ID, "searchButton"))
            )
            search_button.click()
            print("Поиск запущен.")
        except (TimeoutException, ElementClickInterceptedException):
            print("Не удалось нажать кнопку 'Search'.")
            driver.quit()
            return

        try:
            results_container = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "product-list"))
            )
            time.sleep(2)
            products = driver.find_elements(By.CLASS_NAME, "product-list-item")
            print(f"Найдено {len(products)} продуктов.")
        except TimeoutException:
            print("Результаты не отобразились.")
            driver.quit()
            return

        for product in products:
            try:
                title_elem = product.find_element(By.CLASS_NAME, "product-title")
                title_text = title_elem.text.strip()
            except NoSuchElementException:
                continue

            if "Sentinel-1" in title_text:
                try:
                    product.click()
                    print(f"Открыта страница продукта '{title_text}'.")
                except (ElementClickInterceptedException, NoSuchElementException):
                    print(f"Не удалось открыть '{title_text}'.")
                    continue

                try:
                    bands_panel = wait.until(
                        EC.presence_of_element_located((By.ID, "bandsPanel"))
                    )
                except TimeoutException:
                    print("Не удалось найти панель выбора каналов для Sentinel-1.")
                    driver.back()
                    time.sleep(1)
                    continue

                for band_value in ["Band1", "Band2"]:
                    try:
                        checkbox = bands_panel.find_element(
                            By.CSS_SELECTOR, f"input[type='checkbox'][value='{band_value}']"
                        )
                        if not checkbox.is_selected():
                            checkbox.click()
                            print(f"Канал '{band_value}' выбран.")
                    except NoSuchElementException:
                        print(f"Чекбокс канала '{band_value}' не найден.")

                try:
                    download_btn = bands_panel.find_element(By.ID, "downloadBands")
                    download_btn.click()
                    print("Инициировано скачивание Sentinel-1 (2 канала).")
                except NoSuchElementException:
                    print("Кнопка 'Download Selected' не найдена для Sentinel-1.")

                driver.back()
                time.sleep(2)

            elif "Sentinel-2" in title_text:
                try:
                    product.click()
                    print(f"Открыта страница продукта '{title_text}'.")
                except (ElementClickInterceptedException, NoSuchElementException):
                    print(f"Не удалось открыть '{title_text}'.")
                    continue

                try:
                    bands_panel = wait.until(
                        EC.presence_of_element_located((By.ID, "bandsPanel"))
                    )
                except TimeoutException:
                    print("Не удалось найти панель выбора каналов для Sentinel-2.")
                    driver.back()
                    time.sleep(1)
                    continue

                for i in range(1, 14):
                    band_value = f"Band{i}"
                    try:
                        checkbox = bands_panel.find_element(
                            By.CSS_SELECTOR, f"input[type='checkbox'][value='{band_value}']"
                        )
                        if not checkbox.is_selected():
                            checkbox.click()
                            print(f"Канал '{band_value}' выбран.")
                    except NoSuchElementException:
                        print(f"Чекбокс канала '{band_value}' не найден.")

                try:
                    download_btn = bands_panel.find_element(By.ID, "downloadBands")
                    download_btn.click()
                    print("Инициировано скачивание Sentinel-2 (13 каналов).")
                except NoSuchElementException:
                    print("Кнопка 'Download Selected' не найдена для Sentinel-2.")

                driver.back()
                time.sleep(2)

            else:
                continue

        print("Скрипт завершил работу.")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()