import re
import httpx
import uvicorn
import argparse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(name="Macau Weather", json_response=False, stateless_http=False)

# SMG XML API endpoints
URLS = {
    "current": "https://xml.smg.gov.mo/c_actual_brief.xml",  # realtime weather
    "forecast_today": "https://xml.smg.gov.mo/c_forecast.xml",  # today forecast
    "forecast_7days": "https://rss.smg.gov.mo/c_WForecast7days_rss.xml",  # 7 days forecast
    "typhoon": "https://xml.smg.gov.mo/c_typhoon.xml"  # typhoon
}

# Simple in-memory cache
# Structure: {"url": {"data": "content", "date": "YYYY-MM-DD", "timestamp": datetime_obj}}
CACHE = {}

def fetch_content(url: str) -> str:
    """Helper function to fetch raw content."""
    try:
        response = httpx.get(url, timeout=10.0)
        response.raise_for_status()
        return response.text
    except Exception:
        return None


def get_cached_content(url: str, ttl_minutes: int = None) -> str:
    """
    Get content from cache.
    If ttl_minutes is provided, checks if cache is within TTL.
    Otherwise, checks if cache is from the same day.
    """
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    
    # Check cache
    if url in CACHE:
        cached_item = CACHE[url]
        
        is_valid = False
        if ttl_minutes is not None:
            # Check TTL
            if "timestamp" in cached_item:
                age = now - cached_item["timestamp"]
                if age < timedelta(minutes=ttl_minutes):
                    is_valid = True
        else:
            # Check Date (Daily)
            if cached_item["date"] == today:
                is_valid = True

        if is_valid:
            print(f"Using cached data for {url}")
            return cached_item["data"]
    
    # Fetch fresh data
    print(f"Fetching fresh data for {url}")
    content = fetch_content(url)
    if content:
        CACHE[url] = {
            "data": content,
            "date": today,
            "timestamp": now
        }
    return content


def parse_xml(content: str) -> ET.Element:
    """Helper function to parse XML, returns None if parsing fails."""
    try:
        return ET.fromstring(content)
    except ET.ParseError:
        return None


def clean_html(raw_html: str) -> str:
    """Helper function remove HTML tags from string, keeping the text only."""
    if not raw_html:
        return ""
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, ' ', raw_html)
    return cleantext.strip()

@mcp.tool()
def get_macau_realtime_weather() -> str:
    """
    獲取澳門當前「整點實況」天氣數據。
    包含：溫度、濕度、風向、風速、紫外線指數等。
    """
    content = get_cached_content(URLS["current"], ttl_minutes=30)
    if not content:
        return "無法獲取澳門實時天氣數據 (連接失敗)。"
    
    root = parse_xml(content)
    if root is None:
        return "數據格式錯誤 (非 XML)。"

    try:
        data = []
        # get publish time
        pub_time = root.find(".//SysPubdate")
        if pub_time is not None:
            data.append(f"更新時間: {pub_time.text}")
        # get custom data
        custom = root.find("Custom")
        if custom is not None:
            # temperature
            temp = custom.find(".//Temperature/Value")
            if temp is not None:
                data.append(f"當前溫度: {temp.text}°C")
            # humidity
            humidity = custom.find(".//Humidity/Value")
            if humidity is not None:
                data.append(f"相對濕度: {humidity.text}%")
            # wind speed
            wind_speed = custom.find(".//WindSpeed/Value")
            if wind_speed is not None:
                data.append(f"風速: {wind_speed.text} km/h")
            # wind direction
            wind_dir = custom.find(".//WindDirection/WindDescription")
            if wind_dir is not None:
                data.append(f"風向: {wind_dir.text}")
        
        return "\n".join(data) if data else "解析到的實時數據為空。"
    except Exception as e:
        return f"解析實時天氣數據時發生錯誤: {str(e)}"

@mcp.tool()
def get_macau_today_forecast() -> str:
    """
    獲取澳門「今日預測」與天氣概述。
    包含：天氣概況文本、預測溫度範圍。
    """
    content = get_cached_content(URLS["forecast_today"])
    if not content:
        return "無法獲取澳門今日預測數據。"
    
    root = parse_xml(content)
    if root is None:
        return "數據格式錯誤 (非 XML)。"

    try:
        data = []
        # get today forecast
        forecast_item = root.find(".//WeatherForecast")
        if forecast_item is not None:
            # get data
            valid_for = forecast_item.find(".//ValidFor")
            if valid_for is not None and valid_for.text:
                data.append(f"今日日期: {valid_for.text.strip()}")
            # get today situation
            situation = root.find(".//TodaySituation")
            if situation is not None and situation.text:
                data.append(f"天氣形勢: {situation.text.strip()}")
            # get weather description
            forecast_text = forecast_item.find(".//WeatherDescription")
            if forecast_text is not None and forecast_text.text:
                data.append(f"今日天氣概況:\n{forecast_text.text.strip()}")

        return "\n".join(data) if data else "收到數據但無法解析出預測詳情，請嘗試查看實時天氣。"
    except Exception as e:
        return f"解析預測數據錯誤: {str(e)}"

@mcp.tool()
def get_macau_7days_forecast() -> str:
    """
    獲取澳門「7天預測」與天氣概述。
    包含：天氣概況文本、預測溫度範圍。
    """
    content = get_cached_content(URLS["forecast_7days"])
    if not content:
        return "無法獲取澳門7天預測數據。"
    
    root = parse_xml(content)
    if root is None:
        return "數據格式錯誤 (非 XML)。"
    
    try:
        items = root.findall(".//item")
        if not items:
            return "未找到預報條目。"
        first_item = items[0]
        description = first_item.find("description")
        if description is None or not description.text:
            return "未能找到預報詳情，請嘗試查看實時天氣。"
        desc_text = clean_html(description.text)
        forecasts = ""
        day_sections = desc_text.split("預測於")
        for section in day_sections[1:]:
            section = section.strip()
            if not section:
                continue
            # get date
            date_match = re.match(r'^(.*?)\s*溫度:', section)
            if not date_match:
                continue
            date = date_match.group(1).strip()
            # get temperature
            temp = ""
            temp_match = re.search(r'溫度:\s*(.*?)\s*濕度:', section)
            if temp_match:
                temp = temp_match.group(1).strip()
            # get humidity
            humidity = ""
            humid_match = re.search(r'濕度:\s*(.*?)\s*%', section)
            if humid_match:
                humidity = humid_match.group(1).strip() + "%"
            # get weather description
            weather = ""
            weather_match = re.search(r'%\s*(.*)$', section)
            if weather_match:
                weather = weather_match.group(1).strip()
                
            forecasts += f"{date}預測:\n溫度約為{temp}°C，濕度約為{humidity}\n{weather}\n\n"
        return forecasts      
    except Exception as e:
        return f"未能解析到七日預報數據: {str(e)}"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run MCP Streamable HTTP based server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host address to run the server on")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    args = parser.parse_args()

    uvicorn.run(mcp.streamable_http_app, host=args.host, port=args.port)