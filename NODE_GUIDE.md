# SmartCore node guide — from zero to a synced, serving node

Guide covers: install, init, systemd service, peering, optional public RPC,
optional mining, troubleshooting. Time: ~10 minutes.

## 0. Requirements

- Linux x86_64 (Ubuntu 22.04+/Debian 12 recommended)
- 2 GB RAM minimum (`--cache 1024`), 1 GB with `--cache 512`
- 20 GB disk (chain is tiny today, grows ~1 SMC-block per 15-20 s)
- Open TCP port 30399 (or any port you advertise) for P2P

## 1. Download the client

SmartCore runs on the stock OctaSpace geth fork — no patches, exact release
`v2.0.2`:

```bash
mkdir -p ~/smc && cd ~/smc
curl -LO https://github.com/octaspace/go-octa/releases/download/v2.0.2/geth-linux-amd64
chmod +x geth-linux-amd64
./geth-linux-amd64 version   # OctaSpace version 2.0.2
```

## 2. Get the genesis

```bash
curl -LO https://raw.githubusercontent.com/says112/smartcore-node/main/genesis.json
./geth-linux-amd64 --datadir ./data init genesis.json
```

Expected tail: `Successfully wrote genesis block, state root … 0x…`.
If `Error: block number 0 has hash … instead of …` — your genesis is not the
SmartCore one; re-download, do not hand-edit.

## 3. Run the node

Foreground test run first:

```bash
./geth-linux-amd64 --datadir ./data \
  --port 30399 --maxpeers 30 \
  --cache 1024 \
  --http --http.addr 127.0.0.1 --http.port 8548 --http.api eth,net,web3
```

You should see ` Imported new chain segment  number=…` ticking as peers
deliver blocks.

Production systemd unit (`/etc/systemd/system/smc-node.service`):

```ini
[Unit]
Description=SmartCore node
After=network-online.target

[Service]
User=smc
ExecStart=/home/smc/smc/geth-linux-amd64 --datadir /home/smc/smc/data ^
  --port 30399 --maxpeers 30 --cache 1024 ^
  --http --http.addr 127.0.0.1 --http.port 8548 --http.api eth,net,web3
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now smc-node
journalctl -u smc-node -f        # watch imports
```

If your public IP is behind NAT and you want the network to dial you, add
`--nat extip:<YOUR_PUBLIC_IP>`.

## 4. Peering (important on a young chain)

The chain is too small to self-discover quickly. Use our static peers —
create `data/static-nodes.json`:

```json
[
  "enode://823348d874bb5eb855c2c65ec20a0831155f2cf8732c927f2181f08d1782533f0b26b7bdaa9f32d2e1289aa72338c3eb82a988c27dbe872653014a2f5fb6a795@83.221.222.51:30399",
  "enode://51f9e7c3abc9f6f4f2a889f0c0ad55c1c58889f014d16ca6305e0650e9a7b6bf2b53ff64eab79a21671a2ddf29d6a5d52a42ec10907264dd2073e2ea15387cb0@185.207.133.38:30399"
]
```

Restart the node. Attach to verify:

```bash
./geth-linux-amd64 attach --exec 'net.peerCount' http://127.0.0.1:8548
./geth-linux-amd64 attach --exec 'eth.blockNumber' http://127.0.0.1:8548
```

`peers >= 1` and `blockNumber` increasing = synced. (If attach complains
about the http endpoint, use `--exec` with `geth attach http://…` syntax or
start with `--ipcpath`.)

You can also add peers live:

```bash
./geth-linux-amd64 attach --exec 'admin.addPeer("enode://<ID>@<HOST>:30399")' http://127.0.0.1:8548
```

Note: `addPeer` returning `true` only means "queued" — re-check
`net.peerCount` after ~10 s.

## 5. Verify you are on the right chain

```bash
curl -s -X POST -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","id":1,"method":"eth_chainId"}' \
  http://127.0.0.1:8548
# must return 0x138d0  (= 80080)
```

Compare your height with the public RPC:

```bash
curl -s -X POST -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","id":1,"method":"eth_blockNumber"}' \
  https://smartcore.su/smc-rpc
```

Your blockNumber should be within a few blocks of that number.

## 6. Optional: expose RPC to others (safely)

Never expose the raw node RPC. Minimum safe practice — reverse proxy that:

- allows only read methods + `eth_sendRawTransaction` (JSON-RPC body
  inspection), denies `personal_*`, `miner_*`, `admin_*`, `debug_*`, `txpool_*`,
  `eth_getWork`;
- enforces TLS;
- rate-limits by IP.

Production endpoints in this project do exactly that. A reference deny-by-default
filter is in this repo: `scripts/rpc-filter.py` (Python, stdlib only). Run it
in front of geth and put nginx/Caddy TLS in front of it.

## 7. Optional: mine directly to the node

Not recommended for public nodes (`getWork` must be enabled), but for solo
mining on your own machine:

```bash
# create account
./geth-linux-amd64 account new
# start node with --mine --miner.etherbase 0x<ACCOUNT>
# connect miner:
xmrig -a ethash -o http://127.0.0.1:8548 -u 0x<ACCOUNT>.worker -p x
```

For everything else use the pool: `stratum+tcp://smartcore.su:8009`.

## 8. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `peers=0` after restart | static-nodes.json in wrong dir (must be `data/static-nodes.json`, same datadir); or port 30399 blocked inbound — try `--nat extip:IP` and open firewall |
| height stuck at 0 / very old | genesis mismatch (re-init), or all peers unreachable — check the two enodes are reachable: `nc -zv 83.221.222.51 30399` |
| `Failed to unlock account` | you copied someone's unit file with `--unlock`; remove it — unlocking needs the keystore + password and is only for mining nodes |
| node slow / OOM | lower `--cache 512`, add 2 GB swap |
| "unknown network" / fork errors | client version — use OctaSpace geth v2.0.2 exactly (stock go-ethereum cannot validate this chain's custom fields) |
| want archive (explorer) data | add `--gcmode archive --http.api eth,net,web3,debug` (more disk/RAM) |

## 9. Getting help

Discord: https://discord.gg/2rz5BpdA6 (`#майнинг-smartcore` for rigs, general
for node issues). Include `geth version`, height, peerCount when asking.
