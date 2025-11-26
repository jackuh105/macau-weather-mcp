# Macau Weather MCP Server

A Model Context Protocol (MCP) server that provides real-time weather data for Macau from the Macau Meteorological and Geophysics Bureau (SMG). This server exposes weather information through MCP tools, allowing AI assistants to fetch current weather conditions, daily forecasts, and 7-day weather predictions.

## Features

- **Real-time Weather Data**: Get current weather conditions including temperature, humidity, wind speed.
- **Today's Forecast**: Retrieve today's weather forecast with detailed descriptions
- **7-Day Forecast**: Access extended weather predictions for the next 7 days
- **HTTP Streamable MCP**: Built using FastMCP with streamable HTTP support for easy integration
- **Chinese Language Support**: All weather data is provided in Traditional Chinese (繁體中文)

## Requirements

- Python 3.12 or higher
- `uv` package manager (recommended) or `pip`

## Installation

### Using uv (Recommended)

```bash
# Install dependencies
uv sync
```

### Using pip

```bash
# Install dependencies
pip install httpx "mcp[cli]>=1.22.0"
```

## Deployment

Start the MCP server on a specific port:

```bash
# Using uv
uv run weather.py --port 8080

# Or using python directly
python weather.py --port 8080
```

The server will be available at `http://0.0.0.0:8080/mcp` by default.

### Command-line Options

- `--host`: Host address to bind the server (default: `0.0.0.0`)
- `--port`: Port number to listen on (default: `8000`)

## Usage

### OpenWebUI

OpenWebUI requires an MCP-to-OpenAI bridge server (MCPO) to convert MCP tools to OpenAI-compatible tool APIs:

```bash
uvx mcpo --port 8000 --api-key "top-secret" --server-type "streamable-http" -- http://0.0.0.0:8080/mcp
```

Then configure the external tool in OpenWebUI settings. For more MCPO deployment methods, refer to the [official documentation](https://github.com/open-webui/mcpo).

### Claude Desktop

Add the following configuration to your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "macau-weather": {
      "url": "http://localhost:8080/mcp",
      "transport": "http"
    }
  }
}
```

### Other MCP Clients

Any MCP client that supports HTTP streamable transport can connect to this server at:

```
http://localhost:8080/mcp
```

## Available Tools

The server provides three MCP tools:

### 1. `get_macau_realtime_weather`
獲取澳門當前「整點實況」天氣數據，包含：
- 更新時間
- 當前溫度 (°C)
- 相對濕度 (%)
- 風速 (km/h)
- 風向

### 2. `get_macau_today_forecast`
獲取澳門「今日預測」與天氣概述，包含：
- 今日日期
- 天氣形勢
- 今日天氣概況

### 3. `get_macau_7days_forecast`
獲取澳門「7天預測」與天氣概述，包含：
- 每日預測溫度範圍
- 每日濕度預測
- 每日天氣描述

## Data Source

All weather data is sourced from the Macau Meteorological and Geophysical Bureau (SMG) XML APIs:
- Current Weather: `https://xml.smg.gov.mo/c_actual_brief.xml`
- Today's Forecast: `https://xml.smg.gov.mo/c_forecast.xml`
- 7-Day Forecast: `https://rss.smg.gov.mo/c_WForecast7days_rss.xml`

## Technical Details

- **Framework**: FastMCP (MCP server framework)
- **HTTP Client**: httpx
- **Server**: Uvicorn (ASGI server)
- **Data Format**: XML parsing with ElementTree
- **Transport**: HTTP Streamable
