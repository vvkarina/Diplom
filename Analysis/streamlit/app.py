import time
import streamlit as st
from datetime import datetime
import os
import tempfile
import shutil
import base64
import requests

import parser_hub
import preprocessing as preproc
import cropper
import indicies

def home_page():
    st.title("Главная страница")

    with st.expander("1. Скачать снимки"):
        geo_file = st.file_uploader(
            "AOI (GeoJSON, GeoPackage, CSV lon,lat или KML)",
            type=["geojson", "gpkg", "csv", "kml"]
        )
        date = st.date_input("Целевая дата наблюдения", datetime.today())
        download_btn = st.button("Скачать Sentinel-1 (GRD) и Sentinel-2 (L1C) .SAFE")

        if download_btn:
            if not geo_file:
                st.warning("Пожалуйста, загрузите файл для AOI.")
            else:
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(geo_file.name)[1]) as tmp_aoi:
                    tmp_aoi.write(geo_file.getbuffer())
                    tmp_aoi_path = tmp_aoi.name

                with st.spinner("Идет парсинг и скачивание снимков..."):
                    script = f"""
import sys
from parser import main as parser_main

sys.argv = ['parser.py']
from unittest.mock import patch
with patch('builtins.input', side_effect=['{date.strftime('%Y-%m-%d')}', r'{tmp_aoi_path}']):
    parser_main()
"""
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as tmp_script:
                        tmp_script.write(script.encode("utf-8"))
                        tmp_script_path = tmp_script.name

                    os.system(f"python {tmp_script_path}")

                os.remove(tmp_aoi_path)
                os.remove(tmp_script_path)

                st.success("Скачивание Sentinel-1 и Sentinel-2 завершено!")
                st.download_button("⬇️ Скачать Sentinel-2", "sentinel2_data.zip", mime="application/zip")
                st.download_button("⬇️ Скачать Sentinel-1", "sentinel1_data.zip", mime="application/zip")

    with st.expander("2. Предобработка снимков"):
        st.write("1. Sentinel 2: ресемплинг всех каналов в 10м")
        st.write("2. Sentinel 1: удаление граничного и теплового шума, калибровка, ортокоррекция, перевод в дБ")

        st.subheader("Загрузите снимок Sentinel 2")
        sentinel2_file = st.file_uploader("Выберите файл Sentinel-2 (.tif, .tiff, .zip)", type=["tif", "tiff", "zip"], key="s2_preproc")
        if sentinel2_file:
            st.write(f"Загружен файл: {sentinel2_file.name}")

        if st.button("Обработать снимок Sentinel-2"):
            if sentinel2_file:
                with st.spinner("Процесс обработки Sentinel-2..."):
                    temp_dir = tempfile.mkdtemp()
                    s2_path = os.path.join(temp_dir, sentinel2_file.name)
                    with open(s2_path, "wb") as f:
                        f.write(sentinel2_file.getbuffer())
                    output_s2 = os.path.join(temp_dir, "S2_resampled.tif")
                    preproc.process_sentinel2(s2_path, output_s2)
                    st.success("Обработка Sentinel-2 завершена!")
                    with open(output_s2, "rb") as f:
                        st.download_button("⬇️ Сохранить как BigTiff для Sentinel-2", f, file_name="S2_resampled.tif")
                    shutil.rmtree(temp_dir)
            else:
                st.warning("Пожалуйста, загрузите файл Sentinel-2 для обработки.")

        st.write("---")

        st.subheader("Загрузите снимок Sentinel 1")
        sentinel1_file = st.file_uploader("Выберите файл Sentinel-1 (.tif, .tiff, .zip)", type=["tif", "tiff", "zip"], key="s1_preproc")
        if sentinel1_file:
            st.write(f"Загружен файл: {sentinel1_file.name}")

        if st.button("Обработать снимок Sentinel-1"):
            if sentinel1_file:
                with st.spinner("Процесс обработки Sentinel-1..."):
                    temp_dir = tempfile.mkdtemp()
                    s1_path = os.path.join(temp_dir, sentinel1_file.name)
                    with open(s1_path, "wb") as f:
                        f.write(sentinel1_file.getbuffer())
                    output_s1 = os.path.join(temp_dir, "S1_preprocessed_dB.tif")
                    preproc.process_sentinel1(s1_path, output_s1)
                    st.success("Обработка Sentinel-1 завершена!")
                    with open(output_s1, "rb") as f:
                        st.download_button("⬇️ Сохранить как BigTiff для Sentinel-1", f, file_name="S1_preprocessed_dB.tif")
                    shutil.rmtree(temp_dir)
            else:
                st.warning("Пожалуйста, загрузите файл Sentinel-1 для обработки.")

    with st.expander("3. Инференс"):
        geo_file_inf = st.file_uploader("Загрузите файл AOI (GeoJSON, GeoPackage, CSV, KML)", type=["geojson", "gpkg", "csv", "kml"], key="aoi_infer")
        sentinel2_inf = st.file_uploader("Загрузите снимок Sentinel-2 (.tif, .tiff)", type=["tif", "tiff"], key="s2_infer")
        sentinel1_inf = st.file_uploader("Загрузите снимок Sentinel-1 (.tif, .tiff)", type=["tif", "tiff"], key="s1_infer")

        if st.button("Обрезать снимки по AOI"):
            if geo_file_inf and sentinel2_inf and sentinel1_inf:
                temp_dir = tempfile.mkdtemp()
                aoi_path = os.path.join(temp_dir, geo_file_inf.name)
                with open(aoi_path, "wb") as f:
                    f.write(geo_file_inf.getbuffer())

                s2_path = os.path.join(temp_dir, sentinel2_inf.name)
                with open(s2_path, "wb") as f:
                    f.write(sentinel2_inf.getbuffer())
                cropped_s2 = os.path.join(temp_dir, "sentinel2_cropped.tif")
                cropper.clip_image(s2_path, aoi_path, cropped_s2)

                s1_path = os.path.join(temp_dir, sentinel1_inf.name)
                with open(s1_path, "wb") as f:
                    f.write(sentinel1_inf.getbuffer())
                cropped_s1 = os.path.join(temp_dir, "sentinel1_cropped.tif")
                cropper.clip_image(s1_path, aoi_path, cropped_s1)

                st.success("Обрезка завершена!")
                with open(cropped_s2, "rb") as f:
                    st.download_button("⬇️ Скачать обрезанный Sentinel-2", f, file_name="sentinel2_cropped.tif")
                with open(cropped_s1, "rb") as f:
                    st.download_button("⬇️ Скачать обрезанный Sentinel-1", f, file_name="sentinel1_cropped.tif")

                shutil.rmtree(temp_dir)
            else:
                st.warning("Пожалуйста, загрузите все необходимые файлы для обрезки.")

        if st.button("Запустить инференс"):
            if geo_file_inf and sentinel2_inf and sentinel1_inf:
                with st.spinner("Отправка данных на KServe и ожидание ответа..."):
                    temp_dir = tempfile.mkdtemp()

                    aoi_path = os.path.join(temp_dir, geo_file_inf.name)
                    with open(aoi_path, "wb") as f:
                        f.write(geo_file_inf.getbuffer())
                    with open(aoi_path, "rb") as f:
                        aoi_bytes = f.read()
                    aoi_b64 = base64.b64encode(aoi_bytes).decode("utf-8")

                    s2_inf_path = os.path.join(temp_dir, sentinel2_inf.name)
                    with open(s2_inf_path, "wb") as f:
                        f.write(sentinel2_inf.getbuffer())
                    with open(s2_inf_path, "rb") as f:
                        s2_bytes = f.read()
                    s2_b64 = base64.b64encode(s2_bytes).decode("utf-8")

                    s1_inf_path = os.path.join(temp_dir, sentinel1_inf.name)
                    with open(s1_inf_path, "wb") as f:
                        f.write(sentinel1_inf.getbuffer())
                    with open(s1_inf_path, "rb") as f:
                        s1_bytes = f.read()
                    s1_b64 = base64.b64encode(s1_bytes).decode("utf-8")

                    payload = {
                        "instances": [
                            {
                                "aoi": aoi_b64,
                                "sentinel2": s2_b64,
                                "sentinel1": s1_b64
                            }
                        ]
                    }
                    kserve_url = "http://localhost:8080/v1/models/my-model:predict"
                    try:
                        response = requests.post(kserve_url, json=payload, timeout=300)
                        response.raise_for_status()
                        result = response.json().get("predictions", [])
                        st.success("Инференс успешно выполнен!")
                        st.json(result)
                    except requests.exceptions.RequestException as e:
                        st.error(f"Ошибка при обращении к KServe: {e}")

                    shutil.rmtree(temp_dir)
            else:
                st.warning("Пожалуйста, загрузите AOI и оба снимка перед инференсом.")

    with st.expander("4. Расчет индексов"):
        sentinel2_idx = st.file_uploader(
            "Загрузите снимок Sentinel-2 (.tif, .tiff)",
            type=["tif", "tiff"],
            key="s2_indices"
        )
        if sentinel2_idx:
            st.write(f"Загружен файл: {sentinel2_idx.name}")

        if st.button("Рассчитать все индексы"):
            if sentinel2_idx:
                temp_dir = tempfile.mkdtemp()
                s2_idx_path = os.path.join(temp_dir, sentinel2_idx.name)
                with open(s2_idx_path, "wb") as f:
                    f.write(sentinel2_idx.getbuffer())

                import sys
                sys.argv = ['indices.py', s2_idx_path]
                indices.main()

                st.success("Расчет индексов завершен!")
                for name in indices.INDEX_RANGES.keys():
                    png_name = f"{name}_heatmap.png"
                    if os.path.exists(png_name):
                        with open(png_name, "rb") as f:
                            st.download_button(f"⬇️ Скачать {png_name}", f, file_name=png_name)
                        os.remove(png_name)

                shutil.rmtree(temp_dir)
            else:
                st.warning("Пожалуйста, загрузите файл Sentinel-2 для расчета индексов.")

home_page()