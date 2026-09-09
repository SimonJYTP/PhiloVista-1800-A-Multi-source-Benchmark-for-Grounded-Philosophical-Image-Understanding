import csv
import io
import json
import urllib.parse
import urllib.request
import zipfile
import zlib
import time
from pathlib import Path


ROOT = Path(r"D:\Project\哲学AI多模态论文")
MANIFEST = ROOT / "PhiloVista-1800-GitHub" / "final_selection_1800" / "final_selection_manifest.csv"
IMAGES = ROOT / "PhiloVista-1800-images"
OUT = ROOT / "PhiloVista-1800-GitHub" / "audit" / "independent_image_audit_20260908" / "hl_official_remote_index_check.json"
URLS = {
    "train": "https://huggingface.co/datasets/michelecafagna26/hl/resolve/main/data/train.zip",
    "test": "https://huggingface.co/datasets/michelecafagna26/hl/resolve/main/data/test.zip",
}

ALLOWED_REMOTE_HOSTS = {"huggingface.co", "cdn-lfs.huggingface.co", "cdn-lfs-us-1.huggingface.co", "cdn-lfs-eu-1.huggingface.co"}


def assert_safe_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_REMOTE_HOSTS:
        raise ValueError("blocked non-allowlisted url: " + url)
    return url


class RemoteRangeReader(io.RawIOBase):
    def __init__(self, url: str):
        self.url = assert_safe_url(url)
        req = urllib.request.Request(self.url, method="HEAD")
        with urllib.request.urlopen(req, timeout=60) as response:
            self.length = int(response.headers["Content-Length"])
        self.pos = 0

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=io.SEEK_SET):
        if whence == io.SEEK_SET:
            new_pos = offset
        elif whence == io.SEEK_CUR:
            new_pos = self.pos + offset
        elif whence == io.SEEK_END:
            new_pos = self.length + offset
        else:
            raise ValueError(whence)
        if new_pos < 0:
            raise ValueError("negative seek")
        self.pos = min(new_pos, self.length)
        return self.pos

    def read(self, size=-1):
        if self.pos >= self.length:
            return b""
        if size is None or size < 0:
            size = self.length - self.pos
        end = min(self.length - 1, self.pos + size - 1)
        req = urllib.request.Request(assert_safe_url(self.url), headers={"Range": f"bytes={self.pos}-{end}"})
        error = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=120) as response:
                    data = response.read()
                break
            except Exception as exc:
                error = exc
                if attempt < 2:
                    time.sleep(1)
        else:
            raise error
        expected = end - self.pos + 1
        if len(data) != expected:
            raise IOError(f"range response length {len(data)} != {expected}")
        self.pos += len(data)
        return data


def crc32_file(path: Path) -> int:
    value = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value = zlib.crc32(block, value)
    return value & 0xFFFFFFFF


def main():
    with MANIFEST.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = [row for row in csv.DictReader(stream) if row["source"] == "HL Dataset"]
    indexes = {}
    archive_meta = {}
    for split, url in URLS.items():
        remote = RemoteRangeReader(url)
        with zipfile.ZipFile(remote) as archive:
            indexes[split] = {info.filename: info for info in archive.infolist() if not info.is_dir()}
            non_image_members = [
                name for name in indexes[split]
                if Path(name).suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}
            ]
            archive_meta[split] = {
                "url": url,
                "bytes": remote.length,
                "members": len(indexes[split]),
                "sample_members": list(indexes[split])[:5],
                "non_image_members": non_image_members,
            }

    details = []
    for row in rows:
        split = "train" if "train_images" in row["original_container"] else "test"
        name = row["original_member"].replace("\\", "/")
        info = indexes[split].get(name)
        if info is None:
            suffix_matches = [value for key, value in indexes[split].items() if key.endswith("/" + name)]
            if len(suffix_matches) == 1:
                info = suffix_matches[0]
        selected = IMAGES / Path(row["selected_path"]).name
        local_crc = crc32_file(selected)
        details.append({
            "sample_id": row["sample_id"],
            "split": split,
            "member": name,
            "remote_member_found": info is not None,
            "remote_size_matches": info is not None and info.file_size == selected.stat().st_size,
            "remote_crc32_matches": info is not None and info.CRC == local_crc,
        })

    result = {
        "scope": "Official Hugging Face HL train.zip/test.zip central-directory comparison",
        "archive_meta": archive_meta,
        "selected_rows": len(details),
        "remote_member_found": sum(x["remote_member_found"] for x in details),
        "remote_size_matches": sum(x["remote_size_matches"] for x in details),
        "remote_crc32_matches": sum(x["remote_crc32_matches"] for x in details),
        "failures": [x for x in details if not all((x["remote_member_found"], x["remote_size_matches"], x["remote_crc32_matches"]))][:20],
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
