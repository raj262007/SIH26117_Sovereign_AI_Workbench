#!/usr/bin/env python3
"""
Sync local markdown documents to a Notion page.
Target Page: https://app.notion.com/p/Getting-Started-3d13cf56778680d8bdafff52430ca0fc
Page ID: 3d13cf56778680d8bdafff52430ca0fc
"""

import os
import sys
import json
import urllib.request
import urllib.error

NOTION_PAGE_ID = "3d13cf56-7786-80d8-bdaf-ff52430ca0fc"
NOTION_API_VERSION = "2022-06-28"

def get_notion_token():
    token = os.environ.get("NOTION_TOKEN") or os.environ.get("NOTION_API_KEY")
    if not token:
        # Check ~/.env
        env_file = os.path.expanduser("~/.env")
        if os.path.exists(env_file):
            with open(env_file, "r") as f:
                for line in f:
                    if line.startswith("NOTION_TOKEN=") or line.startswith("NOTION_API_KEY="):
                        token = line.strip().split("=", 1)[1].strip().strip('"').strip("'")
                        break
    return token

def create_text_block(text, block_type="paragraph"):
    # Notion text limits: 2000 chars per text block
    truncated_text = text[:2000]
    return {
        "object": "block",
        "type": block_type,
        block_type: {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": truncated_text}
                }
            ]
        }
    }

def markdown_to_blocks(md_content):
    blocks = []
    lines = md_content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        if stripped.startswith("### "):
            blocks.append(create_text_block(stripped[4:], "heading_3"))
        elif stripped.startswith("## "):
            blocks.append(create_text_block(stripped[3:], "heading_2"))
        elif stripped.startswith("# "):
            blocks.append(create_text_block(stripped[2:], "heading_1"))
        elif stripped.startswith("* ") or stripped.startswith("- "):
            blocks.append(create_text_block(stripped[2:], "bulleted_list_item"))
        elif stripped.startswith("```"):
            code_lines = []
            lang = stripped[3:].strip() or "plain text"
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            code_content = "\n".join(code_lines)[:2000]
            blocks.append({
                "object": "block",
                "type": "code",
                "code": {
                    "language": "python" if "python" in lang else ("yaml" if "yaml" in lang else "plain text"),
                    "rich_text": [{"type": "text", "text": {"content": code_content}}]
                }
            })
        elif stripped.startswith("> "):
            blocks.append(create_text_block(stripped[2:], "quote"))
        elif stripped == "---":
            blocks.append({"object": "block", "type": "divider", "divider": {}})
        else:
            blocks.append(create_text_block(stripped, "paragraph"))

        i += 1
    return blocks

def append_blocks_to_page(token, page_id, blocks):
    clean_id = page_id.replace("-", "")
    formatted_id = f"{clean_id[0:8]}-{clean_id[8:12]}-{clean_id[12:16]}-{clean_id[16:20]}-{clean_id[20:32]}"
    url = f"https://api.notion.com/v1/blocks/{formatted_id}/children"

    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_API_VERSION,
        "Content-Type": "application/json"
    }

    # Notion API allows max 100 blocks per request
    chunk_size = 80
    total_chunks = (len(blocks) + chunk_size - 1) // chunk_size

    print(f"Uploading {len(blocks)} blocks in {total_chunks} batches to Notion page {formatted_id}...")

    for chunk_idx in range(total_chunks):
        batch = blocks[chunk_idx * chunk_size : (chunk_idx + 1) * chunk_size]
        payload = json.dumps({"children": batch}).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers=headers, method="PATCH")
        try:
            with urllib.request.urlopen(req) as resp:
                print(f"Batch {chunk_idx + 1}/{total_chunks} uploaded successfully (HTTP {resp.status}).")
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8")
            print(f"Error uploading batch {chunk_idx + 1}: {e.code} - {err_msg}", file=sys.stderr)
            if e.code == 404:
                print("\n[!] 404 Error: Make sure you opened this page in Notion, clicked '...', and selected 'Add connections' -> your integration!", file=sys.stderr)
            sys.exit(1)

def main():
    token = get_notion_token()
    if not token:
        print("[!] Missing NOTION_TOKEN or NOTION_API_KEY environment variable.")
        print("Set it using: export NOTION_TOKEN='secret_...'")
        sys.exit(1)

    doc_path = os.path.join(os.path.dirname(__file__), "SOVEREIGN_AGENTIC_AI_WORKBENCH_SPEC.md")
    if not os.path.exists(doc_path):
        print(f"[!] File not found: {doc_path}")
        sys.exit(1)

    with open(doc_path, "r", encoding="utf-8") as f:
        content = f.read()

    blocks = markdown_to_blocks(content)
    append_blocks_to_page(token, NOTION_PAGE_ID, blocks)
    print("\nSuccessfully synced specification document to Notion!")

if __name__ == "__main__":
    main()
