#!/usr/bin/env python3
# server.py - Python version of the screenshot service

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import Response, PlainTextResponse
from playwright.async_api import async_playwright
from typing import Optional
import logging
import sys
import asyncio

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

app = FastAPI()
PORT = 3000

# Глобальные объекты браузера (инициализируются при старте)
_playwright = None
_browser = None
_render_lock = asyncio.Lock()


@app.on_event("startup")
async def startup_event():
    global _playwright, _browser
    logger.info("Запуск Chromium...")
    _playwright = await async_playwright().start()
    _browser = await _playwright.chromium.launch(
        args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--font-render-hinting=none',
            '--disable-infobars',
            '--disable-dev-shm-usage',  # Использовать /tmp вместо /dev/shm при нехватке памяти
            '--disable-gpu',
        ]
    )
    logger.info(f"Сервис рендеринга запущен на http://0.0.0.0:{PORT}")


@app.on_event("shutdown")
async def shutdown_event():
    global _playwright, _browser
    logger.info("Выгрузка Chromium...")
    if _browser:
        await _browser.close()
    if _playwright:
        await _playwright.stop()
    _playwright = None
    _browser = None
    logger.info("Chromium выгружен")


@app.get("/render")
async def render_screenshot(
    url: str = Query(..., description="URL to screenshot"),
    width: Optional[int] = Query(1280, description="Viewport width"),
    height: Optional[int] = Query(720, description="Viewport height"),
    format: str = Query("png", description="Image format: png, jpeg, or webp"),
    fullPage: str = Query("false", description="Full page screenshot: true or false"),
    quality: Optional[int] = Query(None, description="Quality for jpeg/webp (0-100)"),
    dsf: str = Query("1", description="Device Scale Factor for Retina/HiDPI quality")
):
    """
    Render a screenshot of the given URL.
    """
    if not url:
        raise HTTPException(
            status_code=400,
            detail={
                "error": 'Параметр "url" обязателен.',
                "example": "/render?url=https://example.com"
            }
        )

    if _browser is None:
        raise HTTPException(
            status_code=503,
            detail={"error": "Сервис рендеринга ещё не готов. Chromium запускается."}
        )

    async with _render_lock:
        try:
            last_error = None
            for attempt in range(2):
                try:
                    logger.info(f"Начинаем рендеринг для: {url}" + (f" (повтор {attempt + 1})" if attempt > 0 else ""))

                    device_scale_factor = int(dsf) if dsf.isdigit() else 1

                    # Создаём новую страницу для каждого запроса — изолирует падения и утечки памяти
                    context_to_close = None
                    if device_scale_factor != 1:
                        context_to_close = await _browser.new_context(
                            viewport={"width": width, "height": height},
                            device_scale_factor=device_scale_factor
                        )
                        page = await context_to_close.new_page()
                    else:
                        page = await _browser.new_page()
                        await page.set_viewport_size({"width": width, "height": height})

                    try:
                        logger.info(f"Viewport: {width}x{height}, DeviceScaleFactor: {device_scale_factor}")

                        # Переходим на страницу (domcontentloaded — меньше нагрузка на тяжёлых сайтах)
                        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                        await page.wait_for_timeout(3000)

                        if fullPage.lower() == 'true':
                            await page.evaluate("""
                                async () => {
                                    await new Promise((resolve) => {
                                        let totalHeight = 0;
                                        const distance = 100;
                                        const timer = setInterval(() => {
                                            const scrollHeight = document.body.scrollHeight;
                                            window.scrollBy(0, distance);
                                            totalHeight += distance;

                                            if (totalHeight >= scrollHeight) {
                                                clearInterval(timer);
                                                resolve();
                                            }
                                        }, 100);
                                    });
                                }
                            """)

                        screenshot_options = {
                            "full_page": fullPage.lower() == 'true',
                            "type": format if format in ['png', 'jpeg', 'webp'] else 'png'
                        }

                        if screenshot_options["type"] in ['jpeg', 'webp']:
                            if quality is not None:
                                screenshot_options["quality"] = max(0, min(100, quality))
                            elif screenshot_options["type"] == 'jpeg':
                                screenshot_options["quality"] = 90

                        image_bytes = await page.screenshot(**screenshot_options)

                        logger.info(f"Рендеринг успешно завершен для: {url}")

                        content_type = f"image/{screenshot_options['type']}"
                        return Response(content=image_bytes, media_type=content_type)

                    finally:
                        if context_to_close:
                            await context_to_close.close()
                        else:
                            await page.close()

                except Exception as error:
                    last_error = error
                    if "crashed" in str(error).lower() and attempt == 0:
                        logger.warning(f"Page crashed для {url}, повторная попытка...")
                        continue
                    raise

            if last_error:
                raise last_error

        except Exception as error:
            logger.error(f"Ошибка рендеринга для {url}: {str(error)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Не удалось отрендерить страницу.",
                    "details": str(error)
                }
            )


@app.get("/")
async def root():
    """
    API documentation endpoint.
    """
    return PlainTextResponse(content="""
    API для рендеринга сайтов (v2 - Улучшенное качество)
    ----------------------------------------------------
    Используйте GET-запрос на /render с параметрами.

    Обязательные параметры:
      - url: Адрес сайта для скриншота.

    Необязательные параметры:
      - width: Ширина окна (по умолч. 1280).
      - height: Высота окна (по умолч. 720).
      - format: Формат файла ('png', 'jpeg', 'webp'). По умолч. 'png'.
      - fullPage: Сделать скриншот всей страницы ('true' или 'false'). По умолч. 'false'.
      - dsf: Device Scale Factor для Retina/HiDPI качества (например, '2'). По умолч. '1'.
      - quality: Качество для jpeg/webp от 0 до 100.

    Пример для высокого качества (Retina):
    curl -o site_retina.png "http://localhost:3000/render?url=https://github.com&dsf=2&width=1440&height=900"
    
    Пример для JPEG с максимальным качеством:
    curl -o site_hq.jpeg "http://localhost:3000/render?url=https://apple.com&format=jpeg&quality=100&width=1920&height=1080"
    """, media_type="text/plain; charset=utf-8")


if __name__ == "__main__":
    import uvicorn
    logger.info(f"Сервис рендеринга запущен на http://0.0.0.0:{PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_config=None)
