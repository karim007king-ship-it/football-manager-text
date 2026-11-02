"""Patch the generated p4a manifest before Gradle assembles the APK."""
from pathlib import Path
import xml.etree.ElementTree as ET

ANDROID_NS = "http://schemas.android.com/apk/res/android"
ANDROID_NAME = f"{{{ANDROID_NS}}}name"
ANDROID_HW_ACCEL = f"{{{ANDROID_NS}}}hardwareAccelerated"
TARGET_ACTIVITY = "org.kivy.android.PythonActivity"


def _patch_manifest(path: Path) -> None:
    tree = ET.parse(path)
    root = tree.getroot()
    matches = [
        element
        for element in root.iter()
        if element.tag.rsplit("}", 1)[-1] == "activity"
        and element.get(ANDROID_NAME) == TARGET_ACTIVITY
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one {TARGET_ACTIVITY} in {path}; found {len(matches)}"
        )

    matches[0].set(ANDROID_HW_ACCEL, "false")
    ET.register_namespace("android", ANDROID_NS)
    tree.write(path, encoding="utf-8", xml_declaration=True)

    # Re-read the exact file that Gradle will consume.
    verified = ET.parse(path).getroot()
    activity = [
        element
        for element in verified.iter()
        if element.tag.rsplit("}", 1)[-1] == "activity"
        and element.get(ANDROID_NAME) == TARGET_ACTIVITY
    ]
    if len(activity) != 1 or activity[0].get(ANDROID_HW_ACCEL) != "false":
        raise RuntimeError(f"Manifest verification failed after patch: {path}")
    print(f"VERIFIED: {TARGET_ACTIVITY} hardwareAccelerated=false in {path}")


def after_apk_build(toolchain) -> None:
    """Runs after p4a generates the Gradle project, before Gradle assembles APK."""
    dist_dir = Path(toolchain._dist.dist_dir)
    candidates = [
        dist_dir / "src" / "main" / "AndroidManifest.xml",
        dist_dir / "AndroidManifest.xml",
    ]
    existing = [path for path in candidates if path.is_file()]
    if not existing:
        raise RuntimeError(f"No generated AndroidManifest.xml found under {dist_dir}")

    for manifest in existing:
        _patch_manifest(manifest)
