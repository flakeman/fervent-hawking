import json
import sys
import os
import urllib.request
import urllib.parse

# 1C MCP Server (stdin/stdout JSON-RPC 2.0)
# No external dependencies required.

ODATA_URL = os.environ.get("1C_ODATA_URL", "http://localhost/1c_db/odata/standard.odata/")
ODATA_USER = os.environ.get("1C_ODATA_USER", "Administrator")
ODATA_PASSWORD = os.environ.get("1C_ODATA_PASSWORD", "")
INDEX_FILE = os.environ.get("1C_INDEX_FILE", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "1c_compact_index.json"))

def send_response(rpc_id, result=None, error=None):
    response = {"jsonrpc": "2.0", "id": rpc_id}
    if error is not None:
        response["error"] = error
    else:
        response["result"] = result
    sys.stdout.write(json.dumps(response) + "\n")
    sys.stdout.flush()

def make_odata_request(endpoint, method="GET", data=None):
    url = urllib.parse.urljoin(ODATA_URL, endpoint)
    parsed_url = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed_url.query)
    if "$format" not in query:
        query["$format"] = ["json"]
    new_query = urllib.parse.urlencode(query, doseq=True)
    url = urllib.parse.urlunparse(parsed_url._replace(query=new_query))

    req = urllib.request.Request(url, method=method)
    req.add_header("Accept", "application/json")
    
    if ODATA_USER:
        import base64
        auth_str = f"{ODATA_USER}:{ODATA_PASSWORD}"
        auth_bytes = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
        req.add_header("Authorization", f"Basic {auth_bytes}")

    if data is not None:
        req.add_header("Content-Type", "application/json")
        req_data = json.dumps(data).encode("utf-8")
        req.data = req_data

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            resp_data = response.read().decode("utf-8")
            return json.loads(resp_data)
    except Exception as e:
        return {"error": str(e)}

def handle_request(req):
    method = req.get("method")
    params = req.get("params", {})
    rpc_id = req.get("id")

    if method == "initialize":
        result = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "1c-helper-mcp",
                "version": "1.0.0"
            }
        }
        send_response(rpc_id, result)
        return

    if method == "tools/list":
        tools = [
            {
                "name": "odata_query",
                "description": "Performs a GET query on a 1C OData endpoint (e.g. read catalog, document list or register records).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "endpoint": {"type": "string", "description": "Resource type, e.g. 'Catalog_Номенклатура' or 'Document_СписаниеЗапасов'"},
                        "filter": {"type": "string", "description": "Optional OData filter query, e.g. \"Number eq '000000001'\""},
                        "select": {"type": "string", "description": "Comma-separated list of properties to retrieve, e.g. \"Ref_Key,Description,Code\""},
                        "top": {"type": "integer", "description": "Max number of records to return"}
                    },
                    "required": ["endpoint"]
                }
            },
            {
                "name": "odata_create",
                "description": "Creates a new record or document in 1C via OData POST.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "endpoint": {"type": "string", "description": "Resource type, e.g. 'Catalog_Номенклатура'"},
                        "data": {"type": "object", "description": "JSON object with record properties"}
                    },
                    "required": ["endpoint", "data"]
                }
            },
            {
                "name": "odata_update",
                "description": "Updates an existing 1C record or document using a PATCH request (via Ref_Key guid).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "endpoint": {"type": "string", "description": "Resource type, e.g. 'Catalog_Номенклатура'"},
                        "ref_key": {"type": "string", "description": "GUID of the record to update"},
                        "data": {"type": "object", "description": "Properties to update"}
                    },
                    "required": ["endpoint", "ref_key", "data"]
                }
            },
            {
                "name": "search_config_metadata",
                "description": "Searches a local 1C configuration XML dump for specific metadata files.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "config_dir": {"type": "string", "description": "Path to the unpacked 1C configuration root folder"},
                        "query": {"type": "string", "description": "Object name or pattern to search for, e.g. 'Запасы'"}
                    },
                    "required": ["config_dir", "query"]
                }
            },
            {
                "name": "search_compact_index",
                "description": "Instant in-memory search for 1C metadata tables (catalogs, documents, registers) by name using the prebuilt index.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Word or prefix to look up, e.g. 'Номенклатура' or 'Запасы'"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "extract_xml_query",
                "description": "Extracts 1C query text from a local DataCompositionSchema (DCS) Template.xml file.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "template_path": {"type": "string", "description": "Absolute path to the Template.xml file"}
                    },
                    "required": ["template_path"]
                }
            }
        ]
        send_response(rpc_id, {"tools": tools})
        return

    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name == "odata_query":
            endpoint = arguments.get("endpoint")
            odata_filter = arguments.get("filter")
            select = arguments.get("select")
            top = arguments.get("top")

            query_params = []
            if odata_filter:
                query_params.append(f"$filter={urllib.parse.quote(odata_filter)}")
            if select:
                query_params.append(f"$select={urllib.parse.quote(select)}")
            if top:
                query_params.append(f"$top={top}")

            full_endpoint = endpoint
            if query_params:
                full_endpoint += "?" + "&".join(query_params)

            res = make_odata_request(full_endpoint, "GET")
            send_response(rpc_id, {"content": [{"type": "text", "text": json.dumps(res, ensure_ascii=False, indent=2)}]})
            return

        elif tool_name == "odata_create":
            endpoint = arguments.get("endpoint")
            data = arguments.get("data")
            res = make_odata_request(endpoint, "POST", data)
            send_response(rpc_id, {"content": [{"type": "text", "text": json.dumps(res, ensure_ascii=False, indent=2)}]})
            return

        elif tool_name == "odata_update":
            endpoint = arguments.get("endpoint")
            ref_key = arguments.get("ref_key")
            data = arguments.get("data")
            url_endpoint = f"{endpoint}(guid'{ref_key}')"
            res = make_odata_request(url_endpoint, "PATCH", data)
            send_response(rpc_id, {"content": [{"type": "text", "text": json.dumps(res, ensure_ascii=False, indent=2)}]})
            return

        elif tool_name == "search_config_metadata":
            config_dir = arguments.get("config_dir")
            query = arguments.get("query").lower()
            
            if not os.path.exists(config_dir):
                send_response(rpc_id, error={"code": -32602, "message": f"Config directory does not exist: {config_dir}"})
                return

            matches = []
            subfolders = ["Documents", "Catalogs", "AccumulationRegisters", "InformationRegisters", "Reports"]
            for folder in subfolders:
                folder_path = os.path.join(config_dir, folder)
                if not os.path.exists(folder_path):
                    continue
                for item in os.listdir(folder_path):
                    if query in item.lower():
                        matches.append(os.path.join(folder, item))

            send_response(rpc_id, {"content": [{"type": "text", "text": json.dumps(matches, ensure_ascii=False, indent=2)}]})
            return

        elif tool_name == "search_compact_index":
            query = arguments.get("query").lower()
            if not os.path.exists(INDEX_FILE):
                send_response(rpc_id, error={"code": -32602, "message": f"Metadata index file does not exist. Expected at: {INDEX_FILE}. Please run build_1c_index.py first."})
                return

            try:
                with open(INDEX_FILE, "r", encoding="utf-8") as f:
                    index_data = json.load(f)
                
                results = {}
                for category, items in index_data.items():
                    category_matches = [item for item in items if query in item.lower()]
                    if category_matches:
                        results[category] = category_matches

                send_response(rpc_id, {"content": [{"type": "text", "text": json.dumps(results, ensure_ascii=False, indent=2)}]})
            except Exception as e:
                send_response(rpc_id, error={"code": -32603, "message": f"Error loading index: {str(e)}"})
            return

        elif tool_name == "extract_xml_query":
            template_path = arguments.get("template_path")
            if not os.path.exists(template_path):
                send_response(rpc_id, error={"code": -32602, "message": f"File not exist: {template_path}"})
                return

            try:
                import xml.etree.ElementTree as ET
                tree = ET.parse(template_path)
                root = tree.getroot()
                
                ns = {}
                if root.tag.startswith("{"):
                    ns["default"] = root.tag.split("}")[0][1:]

                queries = []
                query_xpath = ".//default:query" if "default" in ns else ".//query"
                for q in root.findall(query_xpath, ns):
                    if q.text:
                        queries.append(q.text.strip())

                if not queries:
                    send_response(rpc_id, {"content": [{"type": "text", "text": "No queries found in the schema XML."}]})
                else:
                    send_response(rpc_id, {"content": [{"type": "text", "text": "\n\n--- NEXT QUERY ---\n\n".join(queries)}]})
            except Exception as e:
                send_response(rpc_id, error={"code": -32603, "message": f"Error parsing xml: {str(e)}"})
            return

        else:
            send_response(rpc_id, error={"code": -32601, "message": f"Tool not found: {tool_name}"})
            return

    send_response(rpc_id, error={"code": -32601, "message": f"Method not supported: {method}"})

def main():
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            req = json.loads(line)
            handle_request(req)
        except Exception:
            pass

if __name__ == "__main__":
    main()
