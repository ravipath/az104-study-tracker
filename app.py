"""A small, explanation-first Azure VNet and subnet calculator."""

from __future__ import annotations

import ipaddress
from typing import Any

from flask import Flask, render_template, request

app = Flask(__name__)

OCTET_NAMES = ("first", "second", "third", "fourth")


def format_number(value: int) -> str:
    """Render address counts in a scan-friendly form."""
    return f"{value:,}"


def parse_ipv4_cidr(value: str) -> tuple[ipaddress.IPv4Address, ipaddress.IPv4Network]:
    """Parse an IPv4 CIDR while retaining the address the learner entered."""
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Enter an IPv4 address and prefix, such as 10.0.5.23/20.")

    if cleaned.count("/") != 1:
        raise ValueError("Use IPv4 CIDR notation with one prefix, such as 10.0.0.0/16.")

    address_text, prefix_text = (part.strip() for part in cleaned.split("/", 1))
    try:
        entered_address = ipaddress.ip_address(address_text)
    except ValueError as exc:
        raise ValueError("The address must be a valid IPv4 address.") from exc

    if entered_address.version != 4:
        raise ValueError("Azure VNet planning here supports IPv4 CIDR ranges only.")

    try:
        network = ipaddress.ip_network(f"{entered_address}/{prefix_text}", strict=False)
    except ValueError as exc:
        raise ValueError("Use a prefix length from /0 through /32.") from exc

    return entered_address, network


def calculation_for(
    entered_address: ipaddress.IPv4Address, network: ipaddress.IPv4Network
) -> dict[str, Any]:
    """Build the real, human-readable arithmetic for one CIDR range."""
    mask_octets = [int(part) for part in str(network.netmask).split(".")]
    entered_octets = [int(part) for part in str(entered_address).split(".")]
    interesting_index = next(
        (index for index, value in enumerate(mask_octets) if value != 255), None
    )

    # A /32 has no non-255 octet. Treat the last octet as a one-address block so
    # the explanation remains complete even for a non-Azure-sized entered range.
    all_bits_fixed = interesting_index is None
    if interesting_index is None:
        interesting_index = 3

    mask_value = mask_octets[interesting_index]
    block_size = 256 - mask_value
    entered_octet = entered_octets[interesting_index]
    block_start = (entered_octet // block_size) * block_size
    block_end = block_start + block_size - 1
    prefix = network.prefixlen
    total_addresses = network.num_addresses
    azure_usable = total_addresses - 5
    octet_name = OCTET_NAMES[interesting_index]

    if all_bits_fixed:
        interesting_body = (
            "A /32 mask is all 255s, so every bit is fixed. For the block-size "
            "pattern, use the fourth octet as a one-address block."
        )
        interesting_math = "No non-255 octet in 255.255.255.255"
    else:
        interesting_body = (
            f"The {octet_name} octet is the first mask octet that is not 255, "
            "so it is where the address blocks change."
        )
        interesting_math = f"{octet_name.title()} octet: {mask_value}"

    steps = [
        {
            "number": "01",
            "title": "Turn the prefix into a subnet mask",
            "math": f"/{prefix} = {network.netmask}",
            "body": "The prefix counts the network bits from left to right.",
        },
        {
            "number": "02",
            "title": "Find the interesting octet",
            "math": interesting_math,
            "body": interesting_body,
        },
        {
            "number": "03",
            "title": "Calculate the block size",
            "math": f"256 − {mask_value} = {block_size}",
            "body": f"Blocks advance by {block_size} in the {octet_name} octet.",
        },
        {
            "number": "04",
            "title": "Locate the entered address in a block",
            "math": (
                f"{entered_octet} falls in {block_start}–{block_end} "
                f"of the {octet_name} octet"
            ),
            "body": (
                f"The entered address is {entered_address}, so its "
                f"{octet_name} octet is {entered_octet}."
            ),
        },
        {
            "number": "05",
            "title": "Read the network address from that boundary",
            "math": f"Network address = {network.network_address}",
            "body": (
                "Set the host portion to zero at the start of the block. "
                f"The canonical CIDR is {network.with_prefixlen}."
            ),
        },
        {
            "number": "06",
            "title": "Find the final address in the range",
            "math": f"Final address = {network.broadcast_address}",
            "body": "It is the address immediately before the next block begins.",
        },
        {
            "number": "07",
            "title": "Count every address",
            "math": f"2^(32 − {prefix}) = {format_number(total_addresses)}",
            "body": "IPv4 has 32 bits; the prefix leaves the remaining bits for addresses.",
        },
        {
            "number": "08",
            "title": "Apply Azure's reserved-address rule",
            "math": (
                f"{format_number(total_addresses)} − 5 = "
                f"{format_number(azure_usable)}"
            ),
            "body": (
                "Azure reserves the first four addresses and the final address "
                "in every subnet."
            ),
        },
    ]

    return {
        "entered": str(entered_address),
        "canonical": network.with_prefixlen,
        "prefix": prefix,
        "mask": str(network.netmask),
        "network": str(network.network_address),
        "final": str(network.broadcast_address),
        "range": f"{network.network_address} – {network.broadcast_address}",
        "total": total_addresses,
        "total_display": format_number(total_addresses),
        "azure_usable": azure_usable,
        "azure_usable_display": format_number(azure_usable),
        "steps": steps,
    }


def submitted_rows() -> list[dict[str, Any]]:
    """Keep each submitted planner row visible, including rows with errors."""
    names = request.form.getlist("subnet_name")
    cidrs = request.form.getlist("subnet_cidr")
    row_count = max(len(names), len(cidrs), 1)
    rows: list[dict[str, Any]] = []

    for index in range(row_count):
        rows.append(
            {
                "name": names[index].strip() if index < len(names) else "",
                "cidr": cidrs[index].strip() if index < len(cidrs) else "",
                "errors": [],
                "result": None,
            }
        )

    return rows


def validate_subnets(
    rows: list[dict[str, Any]], parent: ipaddress.IPv4Network
) -> list[dict[str, Any]]:
    """Accept only Azure-sized, contained, non-overlapping planner rows."""
    accepted: list[dict[str, Any]] = []

    for row in rows:
        # A blank starter row is an empty state, not a validation problem.
        if not row["name"] and not row["cidr"]:
            continue

        if not row["name"]:
            row["errors"].append("Give this subnet a name so the plan is readable.")
        if not row["cidr"]:
            row["errors"].append("Enter this subnet's IPv4 CIDR range.")
        if row["errors"]:
            continue

        try:
            entered_address, subnet = parse_ipv4_cidr(row["cidr"])
        except ValueError as exc:
            row["errors"].append(str(exc))
            continue

        if subnet.prefixlen > 29:
            row["errors"].append(
                "Azure subnets must be /29 or larger; this range is too small."
            )
        if not subnet.subnet_of(parent):
            row["errors"].append(
                f"{subnet.with_prefixlen} is outside the parent VNet "
                f"{parent.with_prefixlen}."
            )
        overlapping = next(
            (item for item in accepted if subnet.overlaps(item["network"])), None
        )
        if overlapping:
            row["errors"].append(
                f"{subnet.with_prefixlen} overlaps accepted subnet "
                f"“{overlapping['name']}” ({overlapping['network'].with_prefixlen})."
            )

        if row["errors"]:
            continue

        row["result"] = calculation_for(entered_address, subnet)
        accepted.append({"name": row["name"], "network": subnet, "row": row})

    return accepted


@app.route("/", methods=["GET", "POST"])
def index():
    form = {
        "vnet_cidr": "",
        "subnets": [{"name": "", "cidr": "", "errors": [], "result": None}],
    }
    vnet_errors: list[str] = []
    vnet_result: dict[str, Any] | None = None
    accepted: list[dict[str, Any]] = []
    submitted = request.method == "POST"

    if submitted:
        form["vnet_cidr"] = request.form.get("vnet_cidr", "").strip()
        form["subnets"] = submitted_rows()

        try:
            entered_vnet, vnet_network = parse_ipv4_cidr(form["vnet_cidr"])
        except ValueError as exc:
            vnet_errors.append(str(exc))
        else:
            vnet_result = calculation_for(entered_vnet, vnet_network)
            accepted = validate_subnets(form["subnets"], vnet_network)

    return render_template(
        "index.html",
        form=form,
        submitted=submitted,
        vnet_errors=vnet_errors,
        vnet_result=vnet_result,
        accepted=accepted,
    )


@app.route("/health")
def health():
    return {"status": "healthy", "app": "azure-subnet-calculator"}, 200


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
