from venv import logger

import requests
import json
import os
import logging
import streamlit as st
from typing import Generator, Optional, Dict, Any

API_BASE = "http://localhost:8000"


def api_get(path: str) -> dict | list | None:
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("Cannot reach the API server. Make sure the FastAPI backend is running on port 8000.")
        return None
    except Exception as exc:
        st.error(f"API error: {exc}")
        return None


def api_post(path: str, payload: dict) -> dict | None:
    try:
        r = requests.post(f"{API_BASE}{path}", json=payload, timeout=120)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("Cannot reach the API server. Make sure the FastAPI backend is running on port 8000.")
        return None
    except Exception as exc:
        st.error(f"API error: {exc}")
        return None
    
def send_chat_message(
        message: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> Optional[str]:
    """
    Send a chat message and get a complete response
    """
    try:
        payload = {
            "message": message,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p
        }
        
        response = requests.session.post(
            f"{API_BASE}/chat/",
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        
        result = response.json()
        return result.get("response")
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending chat message: {e}")
        return None

def stream_chat_message(
        message: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        top_p: float = 0.9
) -> Generator[str, None, None]:
    """
    Send a chat message and get a streaming response
    """
    try:
        payload = {
            "message": message,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p
        }
        
        with requests.session.post(
            f"{API_BASE}/chat/stream",
            json=payload,
            stream=True,
            timeout=60
        ) as response:
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])  # Remove 'data: ' prefix
                            
                            if 'chunk' in data:
                                yield data['chunk']
                            elif 'done' in data and data['done']:
                                break
                            elif 'error' in data:
                                logger.error(f"Streaming error: {data['error']}")
                                yield f"Error: {data['error']}"
                                break
                                
                        except json.JSONDecodeError:
                            continue
                            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error streaming chat message: {e}")
        yield f"Connection error: {str(e)}"


def fmt_currency(val: float | None) -> str:
    if val is None:
        return "—"
    return f"${val:,.0f}"


def fmt_pct(val: float | None) -> str:
    if val is None:
        return "—"
    return f"{val:.1f}%"