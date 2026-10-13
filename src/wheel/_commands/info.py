"""
Display information about wheel files.
"""

from __future__ import annotations

import email.policy
import sys
from email.parser import BytesParser
from pathlib import Path

from ..wheelfile import WheelFile
from . import escape_control_characters


def info(path: str, verbose: bool = False) -> None:
    """Display information about a wheel file.

    :param path: The path to the wheel file
    :param verbose: Show detailed file listing
    """
    wheel_path = Path(path)
    if not wheel_path.exists():
        raise FileNotFoundError(f"Wheel file not found: {path}")

    with WheelFile(path) as wf:
        # Extract basic wheel information from filename
        parsed = wf.parsed_filename
        name = escape_control_characters(parsed.group("name"))
        version = escape_control_characters(parsed.group("ver"))
        build_tag = escape_control_characters(parsed.group("build") or "")

        print(f"Name: {name}")
        print(f"Version: {version}")
        if build_tag:
            print(f"Build: {build_tag}")

        # Read WHEEL metadata
        try:
            with wf.open(f"{wf.dist_info_path}/WHEEL") as wheel_file:
                wheel_metadata = BytesParser(policy=email.policy.compat32).parse(
                    wheel_file
                )

                wheel_version = escape_control_characters(
                    wheel_metadata.get("Wheel-Version", "Unknown")
                )
                print(f"Wheel-Version: {wheel_version}")
                root_is_purelib = escape_control_characters(
                    wheel_metadata.get("Root-Is-Purelib", "Unknown")
                )
                print(f"Root-Is-Purelib: {root_is_purelib}")

                # Get all tags
                tags = wheel_metadata.get_all("Tag", [])
                if tags:
                    print("Tags:")
                    for tag in sorted(tags):  # Sort tags for consistent output
                        print(f"  {escape_control_characters(tag)}")

                generators = wheel_metadata.get_all("Generator", [])
                for generator in generators:
                    print(f"Generator: {escape_control_characters(generator)}")
        except KeyError:
            print("Warning: WHEEL metadata file not found", file=sys.stderr)

        # Read package METADATA
        try:
            with wf.open(f"{wf.dist_info_path}/METADATA") as metadata_file:
                pkg_metadata = BytesParser(policy=email.policy.compat32).parse(
                    metadata_file
                )

                summary = pkg_metadata.get("Summary", "")
                if summary and summary != "UNKNOWN":
                    print(f"Summary: {escape_control_characters(summary)}")

                author = pkg_metadata.get("Author", "")
                if author and author != "UNKNOWN":
                    print(f"Author: {escape_control_characters(author)}")

                author_email = pkg_metadata.get("Author-email")
                if author_email and author_email != "UNKNOWN":
                    print(f"Author-email: {escape_control_characters(author_email)}")

                homepage = pkg_metadata.get("Home-page")
                if homepage and homepage != "UNKNOWN":
                    print(f"Home-page: {escape_control_characters(homepage)}")

                license_info = pkg_metadata.get("License")
                if license_info and license_info != "UNKNOWN":
                    print(f"License: {escape_control_characters(license_info)}")

                # Show classifiers
                classifiers = pkg_metadata.get_all("Classifier", [])
                if classifiers:
                    print("Classifiers:")
                    for classifier in sorted(
                        classifiers[:5]
                    ):  # Sort and limit to first 5
                        print(f"  {escape_control_characters(classifier)}")

                    if len(classifiers) > 5:
                        print(f"  ... and {len(classifiers) - 5} more")

                # Show dependencies
                requires_dist = pkg_metadata.get_all("Requires-Dist", [])
                if requires_dist:
                    print("Requires-Dist:")
                    for req in sorted(requires_dist):  # Sort dependencies
                        print(f"  {escape_control_characters(req)}")
        except KeyError:
            print("Warning: METADATA file not found", file=sys.stderr)

        # File information
        file_count = len(wf.filelist)
        total_size = sum(zinfo.file_size for zinfo in wf.filelist)

        print(f"Files: {file_count}")
        print(f"Size: {total_size:,} bytes")

        # Show file listing if verbose
        if verbose:
            print("\nFile listing:")
            for zinfo in wf.filelist:
                size_str = f"{zinfo.file_size:,}" if zinfo.file_size > 0 else "0"
                filename = escape_control_characters(zinfo.filename)
                print(f"  {filename:60} {size_str:>10} bytes")
