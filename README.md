# Azure Subnet Calculator

An explanation-first Azure VNet address-space and subnetting calculator for AZ-104 study.

Most subnet calculators stop at the answer. This one shows the working: canonical CIDR normalization, subnet mask, interesting octet, block size, complete range, address count, and Azure's five reserved addresses.

## What it does

- Accepts an IPv4 VNet CIDR, including a host address such as `10.0.5.23/20`
- Normalizes input to the canonical network CIDR
- Shows the subnet mask, network address, final address, and full inclusive range
- Calculates total addresses and Azure-usable addresses
- Walks through eight subnetting steps using the entered values
- Plans multiple named subnets and validates that each one:
  - uses valid IPv4 CIDR notation
  - is contained inside the VNet address space
  - does not overlap an already accepted subnet
  - is Azure-sized at `/29` or larger
- Keeps invalid planner rows visible with plain-language guidance

## Quick start

This project uses [uv](https://docs.astral.sh/uv/) and `pyproject.toml`; it does not use `requirements.txt`.

```bash
cd /home/ravi/az-arena/azure-subnet-calculator
uv sync
uv run flask --app app run --host 127.0.0.1 --port 5000
```

Then open [http://127.0.0.1:5000](http://127.0.0.1:5000).

## A worked example

Enter:

```text
10.0.5.23/20
```

Azure Subnet Calculator will explain:

| Item | Result |
| --- | --- |
| Canonical VNet CIDR | `10.0.0.0/20` |
| Subnet mask | `255.255.240.0` |
| Interesting octet | Third octet, `240` |
| Block size | `256 − 240 = 16` |
| Relevant block | `0–15` |
| Network address | `10.0.0.0` |
| Final address | `10.0.15.255` |
| Total addresses | `2^(32 − 20) = 4,096` |
| Azure-usable addresses | `4,096 − 5 = 4,091` |

For each Azure subnet, the first four addresses and the final address are reserved. The calculator therefore presents both the total address count and the usable count.

## Planning subnets

Add one or more named rows beneath the VNet address space:

```text
web: 10.0.1.0/24
app: 10.0.2.0/24
```

Accepted subnets are listed in a planning table with their canonical CIDR, full range, total capacity, Azure-usable capacity, and an expandable copy of the complete maths.

If a subnet is outside the VNet, overlaps an earlier accepted subnet, or is smaller than `/29`, the calculator describes the issue next to that row and leaves it out of the accepted plan.

## Run the checks

```bash
uv run pytest
```

The tests cover the empty state, CIDR normalization, the worked `/20` explanation, subnet containment, the Azure `/29` minimum, overlap detection, and the health endpoint.

## Project layout

```text
.
├── app.py                  # Flask routes, IP calculations, and validation
├── templates/
│   └── index.html          # Responsive learning interface
├── tests/
│   └── test_app.py         # Behavioural tests
├── pyproject.toml          # uv-managed project metadata and dependencies
└── uv.lock                 # Locked dependency resolution
```

## Health check

```text
GET /health
```

Returns a small JSON status response suitable for a local smoke check.

## Stack

- Python 3.11+
- Flask
- Python standard-library `ipaddress`
- uv
- pytest

---

Built as a practical, beginner-friendly companion for Azure virtual-network and subnetting study.
