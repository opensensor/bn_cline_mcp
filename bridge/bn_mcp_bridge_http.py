#!/usr/bin/env python3
from __future__ import annotations
import json
import time
import logging
from typing import Any, Dict, List, Optional, Tuple
import requests

# Set up logging to help debug connection issues
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Tunables
# ──────────────────────────────────────────────────────────────────────────────
BINJA_URL = "http://localhost:9009"
CONNECT_TIMEOUT = 1.0
READ_TIMEOUT = 8.0
MAX_RETRIES = 2
RETRY_BACKOFF_BASE = 0.2  # seconds
DEFAULT_LIMIT = 100
MAX_LIMIT = 1000   # protect the UI & SSE
CACHE_TTL = 3.0   # seconds for volatile lists

# ──────────────────────────────────────────────────────────────────────────────
# MCP app (synchronous)
# ──────────────────────────────────────────────────────────────────────────────
from fastmcp import FastMCP

mcp = FastMCP("binja-mcp")

def _now() -> float:
    return time.monotonic()

def _request(
    method: str,
    endpoint: str,
    *,
    params: Dict[str, Any] | None = None,
    data: Dict[str, Any] | str | None = None,
) -> Tuple[Optional[Any], Optional[str]]:
    """Wrapped request with retries and error handling."""
    session = requests.Session()
    session.timeout = (CONNECT_TIMEOUT, READ_TIMEOUT)

    last_err = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            url = f"{BINJA_URL}/{endpoint}"
            if method == "GET":
                r = session.get(url, params=params)
            else:
                r = session.post(url, data=data)

            if 200 <= r.status_code < 300:
                # Try JSON; fall back to text split-lines
                try:
                    return r.json(), None
                except json.JSONDecodeError:
                    txt = r.text.strip()
                    if txt.startswith("{") or txt.startswith("["):
                        return json.loads(txt), None
                    return txt.splitlines(), None
            return None, f"{r.status_code} {r.reason}"
        except Exception as e:
            last_err = str(e)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_BASE * (attempt + 1))
            logger.warning(f"Request attempt {attempt + 1} failed: {last_err}")
    return None, last_err or "unknown error"

def _clamp_paging(offset: int | None, limit: int | None) -> Tuple[int, int]:
    o = max(0, int(offset or 0))
    l = min(MAX_LIMIT, max(1, int(limit or DEFAULT_LIMIT)))
    return o, l

# ──────────────────────────────────────────────────────────────────────────────
# Simple TTL cache for volatile list endpoints
# ──────────────────────────────────────────────────────────────────────────────
class TTLCache:
    def __init__(self, ttl: float):
        self.ttl = ttl
        self.store: Dict[Tuple[str, Tuple[Tuple[str, Any], ...]], Tuple[float, Any]] = {}

    def _key(self, name: str, params: Dict[str, Any]) -> Tuple[str, Tuple[Tuple[str, Any], ...]]:
        return (name, tuple(sorted(params.items())))

    def get(self, name: str, params: Dict[str, Any]) -> Optional[Any]:
        k = self._key(name, params)
        item = self.store.get(k)
        if not item:
            return None
        t, val = item
        if _now() - t > self.ttl:
            self.store.pop(k, None)
            return None
        return val

    def set(self, name: str, params: Dict[str, Any], value: Any) -> None:
        k = self._key(name, params)
        self.store[k] = (_now(), value)

ttl_cache = TTLCache(CACHE_TTL)

def _list_endpoint(
    endpoint: str,
    *,
    offset: int,
    limit: int,
    extra: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Generic reader with TTL caching and uniform envelope."""
    params = {"offset": offset, "limit": limit, **(extra or {})}
    cached = ttl_cache.get(endpoint, params)
    if cached is not None:
        return cached

    data, err = _request("GET", endpoint, params=params)
    if err:
        resp = {"ok": False, "error": err, "items": [], "hasMore": False}
        ttl_cache.set(endpoint, params, resp)
        return resp

    # Accept list or JSON dicts from the bridge, normalize to {"items": [...]}.
    if isinstance(data, dict) and "items" in data:
        items = data.get("items", [])
        has_more = bool(data.get("hasMore", False))
    elif isinstance(data, list):
        items = data
        # If bridge can't tell, infer hasMore by requesting +1 (optional).
        has_more = len(items) >= limit  # heuristic
    else:
        items = [data]
        has_more = False

    resp = {"ok": True, "items": items, "hasMore": has_more}
    ttl_cache.set(endpoint, params, resp)
    return resp

# ──────────────────────────────────────────────────────────────────────────────
# Tools (synchronous)
# ──────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def health():
    """
    Cheap health probe for agents. Returns bridge reachability and basic status.
    """
    try:
        status, err = _request("GET", "status")
        return {
            "ok": err is None,
            "error": err,
            "status": status if isinstance(status, (str, dict)) else None,
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"ok": False, "error": str(e), "status": None}

@mcp.tool()
def list_entities(kind: str, offset: int = 0, limit: int = 100, query: str = ""):
    """
    List entities with optional substring filter (where supported by the bridge).
    Valid kinds: methods, classes, segments, imports, exports, data, namespaces
    """
    try:
        # Validate kind parameter
        valid_kinds = ["methods", "classes", "segments", "imports", "exports", "data", "namespaces"]
        if kind not in valid_kinds:
            return {
                "ok": False,
                "error": f"Invalid kind. Must be one of: {', '.join(valid_kinds)}",
                "items": [],
                "hasMore": False
            }

        o, l = _clamp_paging(offset, limit)
        endpoint = kind  # Use kind directly since we validated it

        extra = {}
        # If your bridge has a separate search endpoint for functions:
        if query and kind == "methods":
            # Prefer a dedicated search endpoint
            return _list_endpoint("searchFunctions", offset=o, limit=l, extra={"query": query})
        elif query:
            # If other endpoints eventually support filtering, pass-through
            extra["query"] = query

        return _list_endpoint(endpoint, offset=o, limit=l, extra=extra)
    except Exception as e:
        logger.error(f"Error in list_entities: {e}")
        return {"ok": False, "error": str(e), "items": [], "hasMore": False}

@mcp.tool()
def list_data(offset: int = 0, limit: int = 100, query: str = "", filter_type: str = ""):
    """
    List data items (variables, constants, arrays, etc.) in the binary.

    Parameters:
    - offset: Starting index for pagination (default: 0)
    - limit: Maximum number of items to return (default: 100, max: 1000)
    - query: Optional substring filter for data item names
    - filter_type: Optional filter by data type (e.g., "array", "string", "struct", "global")

    Returns a dictionary with:
    - ok: Success status
    - items: List of data items with details (name, address, size, type, etc.)
    - hasMore: Whether more items are available
    - error: Error message if any
    """
    try:
        o, l = _clamp_paging(offset, limit)

        extra = {}
        if query:
            extra["query"] = query
        if filter_type:
            extra["type"] = filter_type

        # Use the data endpoint
        result = _list_endpoint("data", offset=o, limit=l, extra=extra)

        # Enhance the response with additional context if available
        if result.get("ok") and result.get("items"):
            # Add any additional processing or formatting of data items here
            for item in result["items"]:
                # Ensure consistent structure for data items
                if isinstance(item, dict):
                    # Add default fields if missing
                    item.setdefault("name", "unnamed")
                    item.setdefault("address", None)
                    item.setdefault("size", 0)
                    item.setdefault("type", "unknown")

        return result
    except Exception as e:
        logger.error(f"Error in list_data: {e}")
        return {"ok": False, "error": str(e), "items": [], "hasMore": False}

@mcp.tool()
def get_data_item(name: str = "", address: str = ""):
    """
    Get detailed information about a specific data item.

    Parameters:
    - name: Name of the data item (if known)
    - address: Address of the data item (hex string, e.g., "0x401000")

    At least one of name or address must be provided.

    Returns detailed information about the data item including:
    - name, address, size, type
    - value (if readable)
    - cross-references (functions that use this data)
    - section information
    """
    try:
        if not name and not address:
            return {"ok": False, "error": "Either name or address must be provided"}

        # Prepare the request
        params = {}
        if name:
            params["name"] = name.strip()
        if address:
            params["address"] = address.strip()

        # Request detailed data item information
        data, err = _request("GET", "data/item", params=params)

        if err:
            return {"ok": False, "error": err}

        # Normalize the response
        if isinstance(data, dict):
            return {"ok": True, **data}
        else:
            return {"ok": True, "data": data}

    except Exception as e:
        logger.error(f"Error in get_data_item: {e}")
        return {"ok": False, "error": str(e)}

@mcp.tool()
def read_memory(address: str, size: int, format: str = "hex"):
    """
    Read raw memory/data from the binary at a specific address.

    Parameters:
    - address: Starting address (hex string, e.g., "0x401000")
    - size: Number of bytes to read
    - format: Output format:
        - "hex": Hexadecimal string
        - "bytes": Raw byte array
        - "ascii": ASCII string (non-printable as dots)
        - "hexdump": Formatted hex dump with ASCII

    Returns the memory content in the requested format.
    """
    try:
        if not address:
            return {"ok": False, "error": "Address is required"}
        if size <= 0 or size > 4096:  # Reasonable limit
            return {"ok": False, "error": "Size must be between 1 and 4096 bytes"}

        params = {
            "address": address.strip(),
            "size": size,
            "format": format
        }

        # Request raw memory read
        data, err = _request("GET", "memory", params=params)

        if err:
            return {"ok": False, "error": err}

        return {
            "ok": True,
            "address": address,
            "size": size,
            "format": format,
            "data": data
        }

    except Exception as e:
        logger.error(f"Error in read_memory: {e}")
        return {"ok": False, "error": str(e)}

@mcp.tool()
def search_data_references(address: str = "", pattern: str = ""):
    """
    Search for references to data items in the binary.

    Parameters:
    - address: Address of the data item to find references to
    - pattern: Byte pattern to search for (hex string)

    Returns a list of locations where the data is referenced.
    """
    try:
        if not address and not pattern:
            return {"ok": False, "error": "Either address or pattern must be provided"}

        params = {}
        if address:
            params["address"] = address.strip()
        if pattern:
            params["pattern"] = pattern.strip()

        data, err = _request("GET", "data/references", params=params)

        if err:
            return {"ok": False, "error": err}

        # Format the response
        if isinstance(data, list):
            return {"ok": True, "references": data}
        elif isinstance(data, dict):
            return {"ok": True, **data}
        else:
            return {"ok": True, "references": []}

    except Exception as e:
        logger.error(f"Error in search_data_references: {e}")
        return {"ok": False, "error": str(e)}

@mcp.tool()
def decompile_function(name: str):
    """
    Decompile a function by exact name.
    """
    try:
        if not name or not name.strip():
            return {"ok": False, "error": "Function name cannot be empty"}

        data, err = _request("POST", "decompile", data=name.strip())
        if err:
            return {"ok": False, "error": err}
        # Normalize to JSON
        code = data if isinstance(data, str) else json.dumps(data)
        return {"ok": True, "code": code}
    except Exception as e:
        logger.error(f"Error in decompile_function: {e}")
        return {"ok": False, "error": str(e)}

@mcp.tool()
def get_function_callers(name: str):
    """
    Get all functions that call/reference the specified function.
    
    Parameters:
    - name: Function name or address to find callers for
    
    Returns a dictionary with:
    - ok: Success status
    - function: The function that was searched
    - callers: List of functions that call this function, each with:
        - name: Caller function name
        - address: Caller function address
        - call_site: Address where the call occurs
        - call_context: Disassembly or context of the call
    - count: Number of callers found
    - error: Error message if any
    """
    try:
        if not name or not name.strip():
            return {"ok": False, "error": "Function name cannot be empty"}

        # Try GET request first (it's simpler and more reliable)
        data, err = _request("GET", "function/callers", params={"name": name.strip()})
        
        # If GET fails, try POST as fallback with raw text data
        if err:
            # Send the function name as plain text, not JSON
            data, err = _request("POST", "function/callers", data=name.strip())
        
        if err:
            return {"ok": False, "error": err}
        
        # Parse the response
        if isinstance(data, dict):
            return {"ok": True, **data}
        else:
            return {"ok": False, "error": "Unexpected response format"}
            
    except Exception as e:
        logger.error(f"Error in get_function_callers: {e}")
        return {"ok": False, "error": str(e)}

@mcp.tool()
def overview():
    """
    Get an overview of the loaded binary.
    """
    try:
        data, err = _request("GET", "overview")
        if err:
            return {"ok": False, "error": err}
        return {"ok": True, "overview": data}
    except Exception as e:
        logger.error(f"Error in overview: {e}")
        return {"ok": False, "error": str(e)}

@mcp.tool()
def get_binary_status():
    """
    Get the current binary status and basic information.
    """
    try:
        data, err = _request("GET", "binary")
        if err:
            return {"ok": False, "error": err}
        return {"ok": True, "binary": data}
    except Exception as e:
        logger.error(f"Error in get_binary_status: {e}")
        return {"ok": False, "error": str(e)}

# ──────────────────────────────────────────────────────────────────────────────
# Entrypoint (SSE)
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Starting Binary Ninja MCP SSE Server (synchronous)...")
    print("SSE URL: http://localhost:8010/sse")

    # Test connection on startup
    try:
        logger.info("Testing connection to Binary Ninja bridge...")
        response = requests.get(f"{BINJA_URL}/status", timeout=5.0)
        if response.status_code == 200:
            logger.info("✓ Successfully connected to Binary Ninja bridge")
        else:
            logger.warning(f"⚠ Binary Ninja bridge returned status {response.status_code}")
    except Exception as e:
        logger.error(f"✗ Failed to connect to Binary Ninja bridge: {e}")
        logger.info("Server will start anyway - connection will be retried on first request")

    mcp.run(transport="sse", host="0.0.0.0", port=8010)
