"""Tests for WebSearchService including Shift_JIS Japanese blog decoding."""

from __future__ import annotations

import httpx

from anime_pilgrimage.services.search import WebSearchService


async def test_fetch_page_decodes_shift_jis_without_header_charset():
    """Regression test for Bug 5: Shift_JIS pages with <meta charset> must not garble."""
    html_text = """<!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="Shift_JIS">
        <title>君の名は。聖地巡礼ガイド</title>
    </head>
    <body>
        <article>
            <h1>須賀神社の階段</h1>
            <p>映画『君の名は。』のラストシーンで登場する有名な階段は、東京都新宿区の須賀神社にあります。
            四谷三丁目駅から徒歩約7分でアクセスできます。早朝の訪問がおすすめです。地元の住民の方への配慮を忘れずに撮影しましょう。</p>
        </article>
    </body>
    </html>"""
    shift_jis_bytes = html_text.encode("shift_jis")

    def handler(request: httpx.Request) -> httpx.Response:
        # Deliberately omit charset from Content-Type header (common on older JP blogs)
        return httpx.Response(
            200,
            content=shift_jis_bytes,
            headers={"Content-Type": "text/html"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = WebSearchService(http_client=client)
        page = await service.fetch_page("https://jp-pilgrimage-blog.example/kiminona")

    assert page is not None
    assert "君の名は" in page.title
    assert "須賀神社" in page.text
    assert "四谷三丁目駅" in page.text
    assert "\ufffd" not in page.text


async def test_fetch_page_respects_http_header_charset_without_meta_tag():
    """HTTP Content-Type charset must be passed explicitly to BeautifulSoup as from_encoding."""
    # No <meta charset> tag anywhere in the HTML; charset is ONLY in the HTTP header
    html_text = """<!DOCTYPE html>
    <html>
    <head><title>氷菓 飛騨高山 ロケ地</title></head>
    <body>
        <article>
            <h1>宮川朝市と日枝神社</h1>
            <p>岐阜県高山市にはアニメ『氷菓』の舞台モデルとなった宮川朝市や日枝神社、
            鍛冶橋などのスポットが数多く点在しており、徒歩で巡ることができます。</p>
        </article>
    </body>
    </html>"""
    euc_jp_bytes = html_text.encode("euc_jp")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=euc_jp_bytes,
            headers={"Content-Type": "text/html; charset=EUC-JP"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = WebSearchService(http_client=client)
        page = await service.fetch_page("https://jp-pilgrimage-blog.example/hyouka")

    assert page is not None
    assert "氷菓" in page.title
    assert "日枝神社" in page.text
    assert "宮川朝市" in page.text
    assert "\ufffd" not in page.text
