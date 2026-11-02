#!/usr/bin/env python3
"""Fail the CI build unless both the generated and packaged manifests disable HWUI."""
import argparse
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ANDROID_NS = "http://schemas.android.com/apk/res/android"
ANDROID_NAME = f"{{{ANDROID_NS}}}name"
ANDROID_HW_ACCEL = f"{{{ANDROID_NS}}}hardwareAccelerated"
TARGET_ACTIVITY = "org.kivy.android.PythonActivity"


def verify_text_manifest(path: Path) -> None:
    root = ET.parse(path).getroot()
    activities = [
        item for item in root.iter()
        if item.tag.rsplit("}", 1)[-1] == "activity"
        and item.get(ANDROID_NAME) == TARGET_ACTIVITY
    ]
    if len(activities) != 1 or activities[0].get(ANDROID_HW_ACCEL) != "false":
        raise SystemExit(
            f"FAIL: {TARGET_ACTIVITY} is not uniquely set to hardwareAccelerated=false in {path}"
        )
    print(f"PASS: generated manifest has {TARGET_ACTIVITY} hardwareAccelerated=false")


def verify_apk_manifest(apk: Path, sdk: Path) -> None:
    apkanalyzer = next(sdk.glob("cmdline-tools/*/bin/apkanalyzer"), None)
    if apkanalyzer and apkanalyzer.is_file():
        decoded = subprocess.check_output(
            [str(apkanalyzer), "manifest", "print", str(apk)], text=True
        )
        root = ET.fromstring(decoded)
        activities = [
            item for item in root.iter()
            if item.tag.rsplit("}", 1)[-1] == "activity"
            and item.get(ANDROID_NAME) == TARGET_ACTIVITY
        ]
        if len(activities) != 1 or activities[0].get(ANDROID_HW_ACCEL) != "false":
            raise SystemExit("FAIL: APK manifest does not disable hardware acceleration on PythonActivity")
    else:
        aapt = sorted(sdk.glob("build-tools/*/aapt"))
        if not aapt:
            raise SystemExit("FAIL: neither apkanalyzer nor aapt is available to inspect the APK")
        decoded = subprocess.check_output(
            [str(aapt[-1]), "dump", "xmltree", str(apk), "AndroidManifest.xml"],
            text=True,
        )
        lines = decoded.splitlines()
        found = False
        for index, line in enumerate(lines):
            if re.search(r"\bE: activity(?:\s|$)", line):
                block = []
                for candidate in lines[index + 1:]:
                    if re.match(r"\s*E: ", candidate):
                        break
                    block.append(candidate)
                text = "\n".join(block)
                if TARGET_ACTIVITY in text:
                    found = bool(re.search(
                        r"android:hardwareAccelerated[^\n]*(?:0x0\b|=\s*false\b)",
                        text,
                    ))
                    break
        if not found:
            raise SystemExit("FAIL: APK manifest does not prove hardwareAccelerated=false on PythonActivity")
    print(f"PASS: packaged APK manifest confirms {TARGET_ACTIVITY} hardwareAccelerated=false")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--apk", required=True, type=Path)
    parser.add_argument("--sdk", required=True, type=Path)
    args = parser.parse_args()
    verify_text_manifest(args.manifest)
    verify_apk_manifest(args.apk, args.sdk)


if __name__ == "__main__":
    main()
