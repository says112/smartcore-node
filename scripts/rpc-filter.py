#!/usr/bin/env python3
"""Public JSON-RPC filter proxy for the SMC chain (chainId 80080).

Listens on 127.0.0.1:8549 (nginx https://trade.smartcore.su/smc-rpc -> here)
and forwards whitelisted methods to the node at 127.0.0.1:8548.

Deny-by-default: anything not in ALLOW (personal_*, miner_*, admin_*,
eth_sendTransaction, txpool_*, ...) gets a JSON-RPC error. The public can
READ and submit RAW transactions (MetaMask signs locally) only — an attacker
can never make the node sign from its unlocked pool wallet.
"""
import json
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM = "http://127.0.0.1:8548"
LISTEN = ("127.0.0.1", 8549)

ALLOW = {
    "web3_clientVersion", "web3_sha3",
    "net_version", "net_peerCount", "net_listening",
    "eth_protocolVersion", "eth_syncing", "eth_coinbase", "eth_mining",
    "eth_hashrate", "eth_gasPrice", "eth_accounts", "eth_blockNumber",
    "eth_getBalance", "eth_getStorageAt", "eth_getTransactionCount",
    "eth_getBlockTransactionCountByHash", "eth_getBlockTransactionCountByNumber",
    "eth_getUncleCountByBlockHash", "eth_getUncleCountByBlockNumber",
    "eth_getCode",
    "eth_sendRawTransaction",    "eth_call", "eth_estimateGas", "eth_chainId",
    "eth_getBlockByHash", "eth_getBlockByNumber",
    "eth_getTransactionByHash", "eth_getTransactionByBlockHashAndIndex",
    "eth_getTransactionByBlockNumberAndIndex",
    "eth_getTransactionReceipt", "eth_getUncleByBlockHashAndIndex",
    "eth_getUncleByBlockNumberAndIndex", "eth_getLogs",
    "eth_getCompilers",
    "eth_maxPriorityFeePerGas", "eth_feeHistory",
}


def handle_obj(obj):
    if isinstance(obj, list):
        return [handle_obj(o) for o in obj]
    if not isinstance(obj, dict):
        return {"jsonrpc": "2.0", "error": {"code": -32600, "message": "invalid request"}, "id": None}
    method = obj.get("method", "")
    if method not in ALLOW:
        return {"jsonrpc": "2.0", "id": obj.get("id"),
                "error": {"code": -32601, "message": "method not allowed on public endpoint"}}
    body = json.dumps(obj).encode()
    req = urllib.request.Request(UPSTREAM, data=body,
                                 headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except Exception as e:  # upstream hiccup -> jsonrpc error, not a 500
        return {"jsonrpc": "2.0", "id": obj.get("id"),
                "error": {"code": -32000, "message": f"upstream error: {e}"}}


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _cors(self):
        return {"Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "content-type"}

    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in self._cors().items():
            self.send_header(k, v)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        out = b'{"ok":"smc-rpc-filter: chainId 80080"}'
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def do_POST(self):
        try:
            n = int(self.headers.get("content-length", 0))
        except ValueError:
            self.send_error(400)
            return
        if n < 0 or n > 2_000_000:
            self.send_error(413)
            return
        raw = self.rfile.read(n)
        try:
            obj = json.loads(raw)
        except Exception:
            obj = None
        result = handle_obj(obj) if obj is not None else {
            "jsonrpc": "2.0", "error": {"code": -32700, "message": "parse error"}, "id": None}
        out = json.dumps(result).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        for k, v in self._cors().items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass  # keep journald quiet; nginx access log covers traffic


if __name__ == "__main__":
    ThreadingHTTPServer(LISTEN, H).serve_forever()
