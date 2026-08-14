import os
import json
import logging
import re

from google import genai
from google.genai import types


# ============================================================
# CONFIG
# ============================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not set")


MODEL_NAME = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.1-flash-lite"
)

client = genai.Client(
    api_key=GEMINI_API_KEY
)


# ============================================================
# LOGGING
# ============================================================

logger = logging.getLogger(__name__)


# ============================================================
# PROMPT
# ============================================================

FOOD_ANALYSIS_PROMPT = """
Ты — точный помощник по анализу питания.

Твоя задача — проанализировать фотографию еды.

На фотографии может быть:

1. Этикетка продукта.
2. Готовое блюдо или тарелка с едой.
3. Несколько разных продуктов.
4. Фото еды без упаковки и без таблицы КБЖУ.

Нужно определить тип фотографии и вернуть JSON.

ВАЖНЫЕ ПРАВИЛА:

- Никогда не придумывай значения с этикетки, если они хорошо видны.
- Если на фото готовая еда, оцени состав блюда и размер порций.
- Для готовой еды обязательно используй приблизительную оценку веса каждого продукта.
- Не выдавай оценку готового блюда как точное лабораторное значение.
- Если невозможно определить вес точно, используй разумную приблизительную оценку.
- Не добавляй продукты, которых визуально нет на фотографии.
- Если продукт невозможно уверенно определить, используй наиболее вероятный вариант и снизь confidence.
- Калории и КБЖУ должны соответствовать указанному количеству продукта.
- Все числа должны быть числовыми значениями, без единиц измерения.
- Не используй markdown.
- Ответ должен быть ТОЛЬКО валидным JSON.

--------------------------------------------------
ТИПЫ ФОТО
--------------------------------------------------

Если это упаковка или этикетка:

"type": "label"

Если это готовая еда:

"type": "dish"

Если невозможно определить:

"type": "unknown"

--------------------------------------------------
ЕСЛИ ЭТО LABEL
--------------------------------------------------

Определи:

- название продукта
- калории
- белки
- жиры
- углеводы
- основу значений

basis может быть:

"100g"
"100ml"
"portion"
"package"
"unknown"

Если на этикетке указано несколько вариантов, используй значения, которые наиболее явно относятся к продукту.

--------------------------------------------------
ЕСЛИ ЭТО DISH
--------------------------------------------------

Раздели блюдо на отдельные продукты.

Например:

Фото тарелки с курицей, рисом и овощами:

items:

- Куриная грудка
- Рис
- Овощи

Для каждого продукта определи:

- name
- estimated_grams
- calories
- protein
- fat
- carbs
- confidence

confidence должен быть числом от 0 до 1.

После этого посчитай TOTAL.

--------------------------------------------------
ВАЖНО ПРО ВЕС
--------------------------------------------------

По фотографии невозможно точно узнать вес еды.

Поэтому:

- используй "~" только в человеческом описании, но НЕ в JSON;
- в JSON используй обычное число;
- estimated_grams — это приблизительная оценка;
- учитывай размер тарелки и визуальный объём еды;
- если есть стандартный предмет для масштаба, например вилка, стакан или упаковка, используй его.

--------------------------------------------------
ФОРМАТ LABEL
--------------------------------------------------

{
  "type": "label",
  "name": "Название продукта",
  "calories": 515,
  "protein": 6.7,
  "fat": 29,
  "carbs": 55,
  "basis": "100g",
  "confidence": 0.98
}

--------------------------------------------------
ФОРМАТ DISH
--------------------------------------------------

{
  "type": "dish",
  "name": "Курица с рисом и овощами",
  "items": [
    {
      "name": "Куриная грудка",
      "estimated_grams": 180,
      "calories": 297,
      "protein": 56,
      "fat": 6,
      "carbs": 0,
      "confidence": 0.88
    },
    {
      "name": "Рис",
      "estimated_grams": 150,
      "calories": 195,
      "protein": 4,
      "fat": 0.5,
      "carbs": 42,
      "confidence": 0.82
    }
  ],
  "total": {
    "calories": 492,
    "protein": 60,
    "fat": 6.5,
    "carbs": 42
  },
  "confidence": 0.85
}

--------------------------------------------------
ЕСЛИ UNKNOWN
--------------------------------------------------

{
  "type": "unknown",
  "name": null,
  "calories": null,
  "protein": null,
  "fat": null,
  "carbs": null,
  "basis": "unknown",
  "confidence": 0
}

--------------------------------------------------
ГЛАВНОЕ
--------------------------------------------------

Для готовой еды результат является ОЦЕНКОЙ.

Для этикетки, если значения хорошо видны, используй значения с этикетки.

Не добавляй никаких пояснений вне JSON.
"""


# ============================================================
# JSON CLEANER
# ============================================================

def clean_json_response(text: str) -> str:
    """
    Удаляет markdown-обёртку, если Gemini случайно её добавил.
    """

    if not text:
        return ""

    text = text.strip()

    # ```json ... ```
    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    # ``` ... ```
    text = re.sub(
        r"^```\s*",
        "",
        text
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    return text.strip()


# ============================================================
# VALIDATE NUMBER
# ============================================================

def number_or_none(value):
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# ============================================================
# NORMALIZE RESULT
# ============================================================

def normalize_result(data: dict) -> dict:
    """
    Приводит ответ Gemini к безопасному формату.
    """

    if not isinstance(data, dict):
        raise ValueError(
            "Gemini returned non-dict JSON"
        )

    result_type = data.get(
        "type",
        "unknown"
    )

    if result_type not in (
        "label",
        "dish",
        "unknown"
    ):
        result_type = "unknown"

    # --------------------------------------------------------
    # UNKNOWN
    # --------------------------------------------------------

    if result_type == "unknown":

        return {
            "type": "unknown",
            "name": None,
            "calories": None,
            "protein": None,
            "fat": None,
            "carbs": None,
            "basis": "unknown",
            "confidence": 0.0,
            "items": [],
            "total": {
                "calories": 0.0,
                "protein": 0.0,
                "fat": 0.0,
                "carbs": 0.0
            }
        }

    # --------------------------------------------------------
    # LABEL
    # --------------------------------------------------------

    if result_type == "label":

        return {
            "type": "label",

            "name": (
                data.get("name")
                or "Неизвестный продукт"
            ),

            "calories": number_or_none(
                data.get("calories")
            ),

            "protein": number_or_none(
                data.get("protein")
            ),

            "fat": number_or_none(
                data.get("fat")
            ),

            "carbs": number_or_none(
                data.get("carbs")
            ),

            "basis": (
                data.get("basis")
                or "unknown"
            ),

            "confidence": number_or_none(
                data.get("confidence")
            ) or 0.0,

            "items": [],

            "total": {}
        }

    # --------------------------------------------------------
    # DISH
    # --------------------------------------------------------

    items = data.get(
        "items",
        []
    )

    if not isinstance(items, list):
        items = []

    normalized_items = []

    for item in items:

        if not isinstance(item, dict):
            continue

        normalized_items.append({
            "name": (
                item.get("name")
                or "Неизвестный продукт"
            ),

            "estimated_grams": (
                number_or_none(
                    item.get(
                        "estimated_grams"
                    )
                ) or 0.0
            ),

            "calories": (
                number_or_none(
                    item.get("calories")
                ) or 0.0
            ),

            "protein": (
                number_or_none(
                    item.get("protein")
                ) or 0.0
            ),

            "fat": (
                number_or_none(
                    item.get("fat")
                ) or 0.0
            ),

            "carbs": (
                number_or_none(
                    item.get("carbs")
                ) or 0.0
            ),

            "confidence": (
                number_or_none(
                    item.get("confidence")
                ) or 0.0
            )
        })

    total = data.get(
        "total",
        {}
    )

    if not isinstance(total, dict):
        total = {}

    total_calories = number_or_none(
        total.get("calories")
    )

    total_protein = number_or_none(
        total.get("protein")
    )

    total_fat = number_or_none(
        total.get("fat")
    )

    total_carbs = number_or_none(
        total.get("carbs")
    )

    # Если Gemini не дал total —
    # считаем его из продуктов.
    if total_calories is None:
        total_calories = sum(
            item["calories"]
            for item in normalized_items
        )

    if total_protein is None:
        total_protein = sum(
            item["protein"]
            for item in normalized_items
        )

    if total_fat is None:
        total_fat = sum(
            item["fat"]
            for item in normalized_items
        )

    if total_carbs is None:
        total_carbs = sum(
            item["carbs"]
            for item in normalized_items
        )

    return {
        "type": "dish",

        "name": (
            data.get("name")
            or "Блюдо"
        ),

        "calories": total_calories,

        "protein": total_protein,

        "fat": total_fat,

        "carbs": total_carbs,

        "basis": "dish",

        "confidence": (
            number_or_none(
                data.get("confidence")
            ) or 0.0
        ),

        "items": normalized_items,

        "total": {
            "calories": total_calories,
            "protein": total_protein,
            "fat": total_fat,
            "carbs": total_carbs
        }
    }


# ============================================================
# MAIN ANALYSIS
# ============================================================

async def analyze_food_image(
    image_data: bytes,
    mime_type: str = "image/jpeg"
) -> dict:

    logger.info("=" * 60)
    logger.info("GEMINI FOOD ANALYSIS")
    logger.info("Model: %s", MODEL_NAME)
    logger.info(
        "Image size: %s bytes",
        len(image_data)
    )
    logger.info(
        "MIME type: %s",
        mime_type
    )
    logger.info("=" * 60)

    try:

        response = await client.aio.models.generate_content(
            model=MODEL_NAME,

            contents=[
                types.Part.from_bytes(
                    data=image_data,
                    mime_type=mime_type
                ),
                FOOD_ANALYSIS_PROMPT
            ],

            config=types.GenerateContentConfig(
                temperature=0.1,

                response_mime_type="application/json"
            )
        )

    except Exception as error:

        logger.exception(
            "Gemini API error: %s",
            error
        )

        raise

    raw_text = response.text or ""

    logger.info(
        "GEMINI RAW RESPONSE:\n%s",
        raw_text
    )

    cleaned_text = clean_json_response(
        raw_text
    )

    try:

        parsed = json.loads(
            cleaned_text
        )

    except json.JSONDecodeError as error:

        logger.exception(
            "Could not parse Gemini JSON: %s",
            error
        )

        logger.error(
            "Cleaned response: %s",
            cleaned_text
        )

        raise ValueError(
            "Gemini returned invalid JSON"
        ) from error

    result = normalize_result(
        parsed
    )

    logger.info(
        "GEMINI PARSED RESULT:\n%s",
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        )
    )

    return result
