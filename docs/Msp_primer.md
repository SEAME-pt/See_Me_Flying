# MSP primer: how the ground side talks to INAV

This page explains enough of MSP (MultiWii Serial Protocol) to read the MSP inventory (`inav/msp_inventory.md`) and write code against it. It describes INAV 9.1.0 as used on our drone, reached through esp-link on the ESP12.

## 1. Request and reply

The ground side sends a request naming one message, and INAV sends back exactly one reply. On the MSP port INAV never sends anything by itself, so every value has to be asked for. That is why the inventory gives rates as "replies per second when polled", not as a fixed stream rate.

The path is: ground computer → Wi-Fi → esp-link (TCP port 23) → UART1 → INAV, and the reply comes back the same way. esp-link passes bytes through unchanged, so the ground side speaks plain MSP over TCP.

Our tools send one request, wait for its reply, then send the next. A reply that arrives after its timeout is thrown away, so a late reply is never mistaken for the answer to a later request.

## 2. Framing

Every frame starts with `$`, a version letter (`M` for v1, `X` for v2) and a direction character. Then come the command, the payload size, the payload and a check byte.

```text
MSP v1   $  M  <  size  cmd  payload…  checksum
         size, cmd: 1 byte each
         checksum = XOR of size, cmd and every payload byte

MSP v2   $  X  <  flag  cmd(2)  size(2)  payload…  crc
         flag: 0
         cmd, size: 2 bytes each, little-endian
         crc = CRC8-DVB-S2 (polynomial 0xD5) over flag, cmd, size and payload
```

The direction character is `<` for a request, `>` for a reply and `!` for an error reply.

## 3. v1 versus v2

v1 command IDs fit in one byte (0–255). INAV's own messages start at 0x2000, so they need v2. INAV also answers the old one-byte IDs inside v2 frames, so the team uses v2 for everything: one framing, one checksum, one parser.

## 4. Errors

- **A reply starting `$X!`** means INAV rejected the command or doesn't know it. Our telemetry script then stops polling that message.
- **A wrong check byte** means the bytes were damaged on the link. Discard the frame and treat it like a lost reply.
- **No reply before the timeout** means the request or the reply was lost, usually on Wi-Fi. Count it as loss; the inventory reports loss per message.

## 5. Read versus write

- **Read commands** only answer, and leave the FC unchanged. Everything in the inventory is a read command.
- **Write commands** change the FC's state. For example, `MSP_SET_RAW_RC` (200) sends stick values and can arm the drone. They belong to INAV-6 and its safety limits, and the inventory tools never send them.

One read command has a side effect: polling `MSP_SENSOR_STATUS` (151) makes INAV treat the link as a Configurator connection for one second, which can stop Blackbox logging. It is left out of the inventory for that reason.

## Worked example: asking for the attitude

The request for `MSP_ATTITUDE` (108) in both versions:

```text
v1 request   24 4d 3c 00 6c 6c
             $  M  <  size=0  cmd=108  checksum=0x6c

v2 request   24 58 3c 00 6c 00 00 00 d8
             $  X  <  flag=0  cmd=108 (6c 00)  size=0 (00 00)  crc=0xd8
```

A v2 reply with the drone upside down on the bench:

```text
v2 reply     24 58 3e 00 6c 00 06 00 20 06 33 00 47 01 27
             $  X  >  flag=0  cmd=108  size=6  payload  crc=0x27

payload      20 06 → 0x0620 = 1568 → roll 156.8°   (int16, 0.1°)
             33 00 → 0x0033 =   51 → pitch 5.1°    (int16, 0.1°)
             47 01 → 0x0147 =  327 → heading 327°  (int16, 1°)
```

To check a frame by hand, compute the CRC with `crc8()` from `scripts/msp_inventory.py`, or build a request with its `request(cmd)` function.

## Where to go next

- `inav/msp_inventory.md`: every message we use, its payload layout and its measured rate
- `inav/msp/candidates.md`: why each message was kept or dropped
- `scripts/msp_inventory.py`: a working example of v2 framing, used for the captures and rate tests
- INAV source at the `9.1.0` tag: `src/main/msp/msp_protocol.h`, `src/main/msp/msp_protocol_v2_inav.h` and `src/main/fc/fc_msp.c`
