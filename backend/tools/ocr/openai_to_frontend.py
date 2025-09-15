import argparse
import json
import os
import re
from pathlib import Path

try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except Exception:
    pass


def read_text(input_path: Path) -> str:
    try:
        from .analyze_pdfs import read_text_by_suffix  # type: ignore

        return read_text_by_suffix(input_path)
    except Exception:
        try:
            return input_path.read_text(encoding="utf-8")
        except Exception:
            return input_path.read_text(errors="ignore")


def build_system_prompt() -> str:
    return (
        "你是履歷解析器。請將輸入的履歷全文抽取成嚴格 JSON，鍵名與結構必須完全符合下列規格，且只輸出 JSON：\n"
        "{\n"
        '  "name": string,\n'
        '  "age": string,\n'
        "  \"location\": string (台北市/新北市/桃園市/台中市/台南市/高雄市/新竹市 或 'other'),\n"
        '  "locationOther": string,\n'
        '  "summary": string (<=1000字),\n'
        '  "keywords": string (以逗號分隔的一行字串),\n'
        "  \"expDomain\": string (軟體工程/資料科學/產品/專案 或 'other'),\n"
        '  "expDomainOther": string,\n'
        '  "expLocation": array of string (城市清單),\n'
        '  "expLocationOther": string,\n'
        "  \"remote\": string ('yes'|'no'|'any'),\n"
        '  "workList": [ {\n'
        '     "company": string, "title": string, "start": string(YYYY/MM 或 YYYY/MM), "end": string(YYYY/MM 或 \'Present\'/\'至今\'), \n'
        '     "bullets": array of string\n'
        "  } ],\n"
        '  "eduList": [ {\n'
        '     "school": string, "degree": string(\'Master\'|\'Bachelor\'|\'\'), "major": string, "start": string, "end": string, \n'
        '     "bullets": array of string\n'
        "  } ],\n"
        '  "skillList": array of string,\n'
        '  "projList": [ { "name": string, "desc": string, "tech": array of string, "bullets": array of string } ],\n'
        '  "langList": array of string,\n'
        '  "certList": array of string,\n'
        '  "bioZh": string,\n'
        '  "bioZh2": string\n'
        "}\n"
        "約束：\n"
        "- 僅輸出單一 JSON，不能有任何解說或額外文字\n"
        "- 缺資料以空字串或空陣列填入；日期不確定可留空\n"
        "- 城市與領域若無法判斷，使用 'other'，並在 *Other 欄位補中文\n"
        "- 子彈點內容請以短句呈現\n"
    )


def call_openai(model: str, content: str) -> str:
    from openai import OpenAI  # type: ignore

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("缺少 OPENAI_API_KEY 環境變數")
    client = OpenAI(api_key=api_key)

    sys_prompt = build_system_prompt()
    msg = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": content},
    ]
    # 強制 JSON 輸出
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=msg,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
    except Exception:
        resp = client.chat.completions.create(
            model=model,
            messages=msg,
            temperature=0.2,
        )
    text = resp.choices[0].message.content or ""
    return text


def extract_json(text: str) -> dict:
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{[\s\S]*\}\s*$", text)
    if m:
        return json.loads(m.group(0))
    raise ValueError("回應不是有效 JSON")


CITY_MAP = {
    "Taipei": "台北市",
    "New Taipei": "新北市",
    "Taoyuan": "桃園市",
    "Taichung": "台中市",
    "Tainan": "台南市",
    "Kaohsiung": "高雄市",
    "Hsinchu": "新竹市",
}


def normalize_output(obj: dict) -> dict:
    # 城市正規化
    loc = obj.get("location", "") or ""
    if loc in CITY_MAP:
        obj["location"] = CITY_MAP[loc]
        if not obj.get("locationOther"):
            obj["locationOther"] = ""
    exp_locs = obj.get("expLocation", []) or []
    if isinstance(exp_locs, list):
        norm_locs = []
        for x in exp_locs:
            if x in CITY_MAP:
                norm_locs.append(CITY_MAP[x])
            elif isinstance(x, str) and x:
                norm_locs.append(x)
        obj["expLocation"] = norm_locs

    # keywords 與 skillList 清潔
    def split_keywords(s: str) -> str:
        parts = re.split(r"[，,;；\n]+", s)
        tokens = []
        for p in parts:
            t = p.strip()
            if len(t) >= 2 and not re.fullmatch(r"[\W_]+", t):
                tokens.append(t)
        return ", ".join(tokens[:30])

    if isinstance(obj.get("keywords"), str):
        obj["keywords"] = split_keywords(obj["keywords"])[:500]
    if isinstance(obj.get("skillList"), list):
        cleaned = []
        for s in obj["skillList"]:
            if not isinstance(s, str):
                continue
            parts = re.split(r"[•·\n]+", s)
            for p in parts:
                t = p.strip()
                if len(t) >= 2:
                    cleaned.append(t)
        # 去重與截斷
        seen = set()
        uniq = []
        for t in cleaned:
            if t not in seen:
                seen.add(t)
                uniq.append(t)
        obj["skillList"] = uniq[:50]

    # workList/eduList bullets 切分
    for key in ("workList", "eduList", "projList"):
        arr = obj.get(key, []) or []
        if not isinstance(arr, list):
            continue
        for item in arr:
            bs = item.get("bullets", []) if isinstance(item, dict) else []
            if isinstance(bs, list):
                new_b = []
                for s in bs:
                    if not isinstance(s, str):
                        continue
                    parts = re.split(r"[•·\n]+", s)
                    for p in parts:
                        t = p.strip()
                        if len(t) >= 4:
                            new_b.append(t)
                item["bullets"] = new_b[:10]

    # summary 截斷
    if isinstance(obj.get("summary"), str):
        obj["summary"] = obj["summary"][:1000]

    # 必要欄位預設
    for k in [
        "name",
        "age",
        "location",
        "locationOther",
        "summary",
        "keywords",
        "expDomain",
        "expDomainOther",
        "expLocation",
        "expLocationOther",
        "remote",
        "workList",
        "eduList",
        "skillList",
        "projList",
        "langList",
        "certList",
        "bioZh",
        "bioZh2",
    ]:
        if k not in obj:
            obj[k] = [] if k.endswith("List") else ""

    return obj


def process_one(input_path: Path, out_dir: Path, model: str, max_chars: int) -> Path:
    out_path = out_dir / f"{input_path.stem}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 前處理清洗（重用 cluster_parser 的規則）
    text = read_text(input_path)
    try:
        from .cluster_parser import preprocess_text  # type: ignore

        text = preprocess_text(text)
    except Exception:
        pass
    if len(text) > max_chars:
        text = text[:max_chars]

    raw = call_openai(model, text)
    data = extract_json(raw)
    data = normalize_output(data)
    out_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return out_path


def main() -> None:
    p = argparse.ArgumentParser(
        description="Use OpenAI to extract resume into frontend JSON schema"
    )
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--input-file", help="Input file (.pdf/.docx/.doc/.txt)")
    g.add_argument("--input-dir", help="Input directory containing resumes")
    p.add_argument(
        "--out",
        default="",
        help="Output json path (single file) or output directory (for --input-dir). Default: output_frontend",
    )
    p.add_argument(
        "--model", default="gpt-4o-mini", help="OpenAI model (default: gpt-4o-mini)"
    )
    p.add_argument(
        "--max-chars",
        type=int,
        default=60000,
        help="Max characters to send (default: 60000)",
    )
    args = p.parse_args()

    if args.input_file:
        input_path = Path(args.input_file)
        out_path = (
            Path(args.out)
            if args.out and args.out.lower().endswith(".json")
            else Path(args.out or "output_frontend") / f"{input_path.stem}.json"
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        written = process_one(input_path, out_path.parent, args.model, args.max_chars)
        print(f"Wrote: {written}")
        return

    # directory mode
    in_dir = Path(args.input_dir)
    out_dir = Path(args.out or "output_frontend")
    out_dir.mkdir(parents=True, exist_ok=True)
    patterns = ["*.pdf", "*.docx", "*.doc", "*.txt"]
    files = []
    for pat in patterns:
        files.extend(in_dir.glob(pat))
    files = sorted(files)
    if not files:
        print("No input files found.")
        return
    for f in files:
        try:
            written = process_one(f, out_dir, args.model, args.max_chars)
            print(f"Wrote: {written}")
        except Exception as exc:
            print(f"Skip {f.name}: {exc}")


if __name__ == "__main__":
    main()
