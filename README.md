# SmartCore node (geth fork) — chain launch kit

SmartCore: custom public PoW ethash chain, chainId **80080** (0x138d0),
1 SMC per block, premine 10.1M SMC. GPU miners (ethash) and ASIC-class
firmwares both work; a CPU `--mine` node keeps the chain live between miners.

## Files
- `genesis.json` — production genesis (import as-is)
- `NODE_GUIDE.md` — full step-by-step: install → systemd → peering → safe RPC → troubleshooting
- `scripts/rpc-filter.py` — deny-by-default JSON-RPC filter proxy (stdlib only) used on public endpoints

## Run a node (Ubuntu/Debian)
```
geth --datadir ./smc init genesis.json
geth --datadir ./smc --port 30399 --http --http.addr 127.0.0.1 --http.port 8548 \
     --http.api eth,net,web3 --maxpeers 30
```
## Binary
The node client is the OctaSpace geth fork (upstream, unmodified):
releases at https://github.com/octaspace/go-octa/releases
(we run v2.0.2 `geth-linux-amd64`; docker: `octaspace/go-octa`).
SmartCore ships no node patches — the chain runs on the stock client with
our `genesis.json`.

## Public endpoints
- RPC (filtered, read-only + `eth_sendRawTransaction`):
  - https://smartcore.su/smc-rpc
  - https://explorer.smartcore.su/smc-rpc
  - https://trade.smartcore.su/smc-rpc
  - https://rpc.smartcore.su
- Explorer: https://explorer.smartcore.su
- MetaMask chainId: 80080, currency SMC.

## Peering
Static peers (replace node enode with yours):
```
geth attach --exec 'admin.nodeInfo'
# add to static-nodes.json in datadir:
["enode://<PEER_ID>@<PEER_HOST>:30399"]
```

## Do not expose
Never publish raw node RPC: use a deny-by-default JSON-RPC filter
(read methods + eth_sendRawTransaction only). Public `eth_getWork`,
`personal_*`, `miner_*`, `admin_*` = theft/DDoS vector.
