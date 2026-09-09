import csv
import hashlib
import io
import json
import re
import unicodedata
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

from verify_remote_hl_zip_index import RemoteRangeReader, URLS


ROOT = Path(r"D:\Project\哲学AI多模态论文")
HL_ROOT = ROOT / "NewBenchmark" / "PhilosophyHL_v3" / "source_extracted" / "hl_dataset_export"
MANIFEST = ROOT / "PhiloVista-1800-GitHub" / "final_selection_1800" / "final_selection_manifest.csv"
OUT = Path(__file__).resolve().parent / "hl_official_metadata_and_pixel_check.json"


def load_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def split_captions(value: str):
    return [part.strip() for part in value.split("；")]


def pixel_hash(image):
    rgb = image.convert("RGB")
    return rgb.size, hashlib.sha256(rgb.tobytes()).hexdigest()


def normalize_caption(value):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value)).strip()


def normalized_list(values):
    return [normalize_caption(value) for value in values]


def dhash(image):
    gray = image.convert("L").resize((9, 8))
    pixels = list(gray.getdata())
    value = 0
    for row in range(8):
        for col in range(8):
            value = (value << 1) | (pixels[row * 9 + col] > pixels[row * 9 + col + 1])
    return value


def pick_evenly(rows, count):
    if len(rows) <= count:
        return rows
    return [rows[round(i * (len(rows) - 1) / (count - 1))] for i in range(count)]


def main():
    manifest = [row for row in load_csv(MANIFEST) if row["source"] == "HL Dataset"]
    selected_by_split = {
        split: [row for row in manifest if split + "_images" in row["original_container"]]
        for split in ("train", "test")
    }
    split_results = {}
    sample_results = []

    for split in ("train", "test"):
        remote = RemoteRangeReader(URLS[split])
        import zipfile
        with zipfile.ZipFile(remote) as archive:
            metadata = [
                json.loads(line)
                for line in archive.read(f"{split}/metadata.jsonl").decode("utf-8").splitlines()
                if line.strip()
            ]
            local_rows = load_csv(HL_ROOT / f"{split}_annotations.csv")
            exact = 0
            normalized_exact = 0
            mismatch_examples = []
            for local, official in zip(local_rows, metadata):
                captions = official["captions"]
                local_axes = {
                    "scene": split_captions(local["Scene场景描述"]),
                    "action": split_captions(local["Action动作描述"]),
                    "rationale": split_captions(local["Rationale理由描述"]),
                    "object": split_captions(local["Object物体描述"]),
                }
                row_exact = (
                    local_axes["scene"] == captions["scene"]
                    and local_axes["action"] == captions["action"]
                    and local_axes["rationale"] == captions["rationale"]
                    and local_axes["object"] == captions["object"]
                )
                exact += row_exact
                row_normalized = all(
                    normalized_list(local_axes[axis]) == normalized_list(captions[axis])
                    for axis in ("scene", "action", "rationale", "object")
                )
                normalized_exact += row_normalized
                if not row_normalized and len(mismatch_examples) < 3:
                    mismatch_examples.append({
                        "local_file": local["图片文件名"],
                        "official_file": official["file_name"],
                        "local": local_axes,
                        "official": captions,
                    })

            sample_count = 5 if split == "train" else 3
            samples = pick_evenly(
                sorted(
                    selected_by_split[split],
                    key=lambda r: int(r["source_id"].split("_")[1].split(".")[0]),
                ),
                sample_count,
            )
            for row in samples:
                index = int(row["source_id"].split("_")[1].split(".")[0])
                official = metadata[index]
                remote_name = f"{split}/{official['file_name']}"
                remote_bytes = archive.read(remote_name)
                with Image.open(io.BytesIO(remote_bytes)) as remote_image:
                    remote_size, remote_hash = pixel_hash(remote_image)
                    remote_rgb = remote_image.convert("RGB")
                    remote_dhash = dhash(remote_image)
                local_path = HL_ROOT / f"{split}_images" / row["source_id"]
                with Image.open(local_path) as local_image:
                    local_size, local_hash = pixel_hash(local_image)
                    local_rgb = local_image.convert("RGB")
                    local_dhash = dhash(local_image)
                diff = ImageChops.difference(local_rgb, remote_rgb)
                diff_stat = ImageStat.Stat(diff)
                sample_results.append({
                    "sample_id": row["sample_id"],
                    "local_export": row["source_id"],
                    "official_member": remote_name,
                    "dimensions_match": local_size == remote_size,
                    "decoded_rgb_sha256_match": local_hash == remote_hash,
                    "dhash_hamming": (local_dhash ^ remote_dhash).bit_count(),
                    "mean_absolute_channel_difference": round(sum(diff_stat.mean) / 3, 4),
                })

        split_results[split] = {
            "official_metadata_rows": len(metadata),
            "local_annotation_rows": len(local_rows),
            "caption_rows_exact": exact,
            "caption_rows_normalized_exact": normalized_exact,
            "normalized_mismatch_examples": mismatch_examples,
        }

    result = {
        "scope": "Official HL Hugging Face metadata full comparison plus deterministic decoded-pixel sample",
        "split_results": split_results,
        "selected_pixel_sample": len(sample_results),
        "sample_dimensions_match": sum(x["dimensions_match"] for x in sample_results),
        "sample_decoded_rgb_sha256_match": sum(x["decoded_rgb_sha256_match"] for x in sample_results),
        "sample_dhash_within_2": sum(x["dhash_hamming"] <= 2 for x in sample_results),
        "sample_mean_abs_diff_under_2": sum(x["mean_absolute_channel_difference"] < 2 for x in sample_results),
        "sample_failures": [x for x in sample_results if x["dhash_hamming"] > 2 or x["mean_absolute_channel_difference"] >= 2],
        "samples": sample_results,
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "samples"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
