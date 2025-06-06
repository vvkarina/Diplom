## Выпускная квалификационная работа
Тема: Интеграция модели удаления облаков в производственный пайплайн обработки спутниковых снимков

## Описание
Этот проект содержит инструменты для работы со спутниковыми снимками Sentinel-1 и Sentinel-2:
- **parser.py** — парсинг и скачивание данных через Selenium
- **preprocessing.py** — предобработка в ESA SNAP (snappy)
- **cropper.py** — обрезка по AOI из KML/GeoJSON
- **indices.py** — расчёт вегетационных индексов и построение тепловых карт
- **app.py** (Streamlit) — веб-интерфейс для всех описанных функций

---

## 1. Клонирование репозитория

1. Откройте терминал (командную строку).
2. Перейдите в папку, в которой хотите разместить проект:
   ```bash
   cd /путь/к/папке_с_проектами
   ```
3. Склонируйте репозиторий с GitHub:
   ```bash
    git clone https://github.com/vvkarina/Diplom.git
   ```
4. Перейдите в только что созданную папку проекта:
   ```bash
    cd Diplom
   ```

---

## 2. Установка зависимостей

Установите все необходимые пакеты из `requirements.txt`:
   ```bash
   pip install -r requirements.txt   
   ```

Модули ESA SNAP (`snappy`) — при этом SNAPPY обычно устанавливается отдельно через дистрибутив ESA SNAP.  
> - Если у вас ещё не установлен ESA SNAP, скачайте и установите его с официального сайта:  
>   https://step.esa.int/main/download/

---

## 3. Настройка ESA SNAP (snappy)

1. Скачайте и установите ESA SNAP Desktop (версия **≥ 8.0**).
2. Пропишите переменные окружения для Snappy (пример для Linux/macOS):
   ```bash
   export SNAPPY_HOME=/path/to/snap
   export PATH=$SNAPPY_HOME/bin:$PATH
   ```
   Для Windows (через «Переменные среды»):
   ```
   SNAPPY_HOME=C:\Program Files\snap
   PATH=%SNAPPY_HOME%\bin;%PATH%
   ```
3. Убедитесь, что `snappy` доступен в Python. В терминале выполните:
   ```bash
    python - <<EOF
    from snappy import ProductIO, GPF
    GPF.getDefaultInstance().getOperatorSpiRegistry().loadOperatorSpis()
    print("Snappy OK")
    EOF
   ```
   Если ошибок нет, значит Snappy настроен корректно.

---

## 4. Запуск Streamlit

После установки зависимостей в корне проекта появится файл `app.py`. Чтобы запустить веб-интерфейс:

1. Убедитесь, что виртуальное окружение (если оно есть) активировано.
2. В терминале выполните:
   ```bash
   streamlit run app.py
   ```
3. Откроется новое окно браузера (или вкладка) с приложением Streamlit.  
   Если браузер не открылся автоматически, перейдите по адресу:
   ```
   http://localhost:8501
   ```
