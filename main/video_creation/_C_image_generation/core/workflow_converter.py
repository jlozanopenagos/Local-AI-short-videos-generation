"""
workflow_converter.py — Converts a ComfyUI node-editor JSON (UI format)
into the flat API prompt format required by POST /prompt.

The node-editor format stores nodes as a list under "nodes" and connections
as a list under "links".  The API format is a dict keyed by node-ID string,
where each value has "class_type" and "inputs".

    Node-editor format  →  API format
    ─────────────────────────────────
    nodes[i].id         →  str(node.id)  (top-level key)
    nodes[i].type       →  class_type
    nodes[i].widgets_values[n] → inputs[widget_name]  (positional mapping)
    links               →  inputs[input_name] = [src_node_id_str, src_slot]

Only the nodes that have a "class_type" registered in ComfyUI need to be
submitted; PrimitiveNode entries that expose a widget via a link are resolved
as literal values rather than nodes.

Usage
─────
    from core.workflow_converter import convert_workflow
    api_prompt = convert_workflow(workflow_dict)
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── Widget name tables ────────────────────────────────────────────────────────
# Maps class_type → ordered list of widget names as ComfyUI defines them.
# Only the node types present in AcademiaSD_Z-Image.json are listed here.
# Extend this table if you add nodes to the workflow.

_WIDGET_NAMES: dict[str, list[str]] = {
    "KSampler": [
        "seed", "control_after_generate", "steps", "cfg",
        "sampler_name", "scheduler", "denoise",
    ],
    "CLIPTextEncode": ["text"],
    "EmptySD3LatentImage": ["width", "height", "batch_size"],
    "VAELoader": ["vae_name"],
    "CLIPLoader": ["clip_name", "type", "device"],
    "LoaderGGUFAdvanced": [
        "gguf_name", "dequant_dtype", "patch_dtype", "patch_on_device",
    ],
    "SaveImage": ["filename_prefix"],
    # rgthree Power Lora Loader — widgets_values contains JSON blobs;
    # there are no simple scalar widgets that need injection, so omit.
    "Power Lora Loader (rgthree)": [],
}

# Node types that are UI-only helpers and should NOT be submitted to the API.
_UI_ONLY_TYPES = {
    "PrimitiveNode",
    "Note",
    "Reroute",
}


def _build_link_map(workflow: dict[str, Any]) -> dict[int, tuple[int, int]]:
    """
    Returns a mapping  link_id → (source_node_id, source_slot_index)
    built from workflow["links"].

    Each link entry is:  [link_id, src_node_id, src_slot, dst_node_id, dst_slot, type]
    """
    link_map: dict[int, tuple[int, int]] = {}
    for link in workflow.get("links", []):
        link_id, src_node_id, src_slot = link[0], link[1], link[2]
        link_map[link_id] = (src_node_id, src_slot)
    return link_map


def _primitive_value_map(workflow: dict[str, Any]) -> dict[int, Any]:
    """
    Returns a mapping  node_id → scalar value  for every PrimitiveNode.
    PrimitiveNodes expose a single widget value (widgets_values[0]) via a link.
    When a regular node's input is linked to a PrimitiveNode, we inline the
    scalar rather than referencing the PrimitiveNode as a node.
    """
    prim: dict[int, Any] = {}
    for node in workflow.get("nodes", []):
        if node.get("type") == "PrimitiveNode":
            values = node.get("widgets_values", [])
            if values:
                prim[node["id"]] = values[0]
    return prim


def convert_workflow(workflow: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a node-editor format workflow dict into the ComfyUI API prompt dict.

    Returns a dict suitable for use as the value of ``{"prompt": <result>}``.
    """
    link_map    = _build_link_map(workflow)
    prim_values = _primitive_value_map(workflow)

    # Index all nodes by their integer ID for fast lookup
    nodes_by_id: dict[int, dict[str, Any]] = {
        n["id"]: n for n in workflow.get("nodes", [])
    }

    api_prompt: dict[str, Any] = {}

    for node in workflow.get("nodes", []):
        node_type = node.get("type", "")

        # Skip UI-only helper nodes
        if node_type in _UI_ONLY_TYPES:
            continue

        node_id  = str(node["id"])
        class_type = node_type

        inputs: dict[str, Any] = {}

        # ── 1. Resolve linked inputs ──────────────────────────────────────────
        for inp in node.get("inputs", []):
            inp_name = inp.get("name", "")
            link_id  = inp.get("link")

            if link_id is None:
                # Not connected — value comes from widgets_values (handled below)
                continue

            if link_id not in link_map:
                logger.warning(
                    "Node %s input '%s': link %s not found in links table.",
                    node_id, inp_name, link_id,
                )
                continue

            src_node_id, src_slot = link_map[link_id]

            # If the source is a PrimitiveNode, inline its scalar value
            if src_node_id in prim_values:
                inputs[inp_name] = prim_values[src_node_id]
            else:
                # Reference the source node and output slot
                inputs[inp_name] = [str(src_node_id), src_slot]

        # ── 2. Map widget values to named inputs ──────────────────────────────
        widget_names = _WIDGET_NAMES.get(class_type, [])
        widgets_vals = node.get("widgets_values", [])

        # Only map widgets that are NOT already satisfied by a link
        widget_idx = 0
        for w_name in widget_names:
            if w_name in inputs:
                # This widget position is consumed by a link — skip the value
                # BUT we still need to advance the widget index if the node
                # stores the widget value regardless of link state.
                # ComfyUI always stores widget values in widgets_values even
                # when a link is connected, so we must advance the counter.
                widget_idx += 1
                continue
            if widget_idx < len(widgets_vals):
                inputs[w_name] = widgets_vals[widget_idx]
            widget_idx += 1

        api_prompt[node_id] = {
            "class_type": class_type,
            "inputs": inputs,
        }

    logger.debug("Converted workflow: %d nodes → %d API nodes", len(workflow.get("nodes", [])), len(api_prompt))
    return api_prompt
