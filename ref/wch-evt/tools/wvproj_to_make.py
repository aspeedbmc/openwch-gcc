#!/usr/bin/env python3
"""Convert a WCH MounRiver ``.wvproj`` into an independent Makefile.

The converter deliberately writes into a separate output directory.  It never
edits the EVT project, its source files, or its Eclipse metadata.

MounRiver releases in the EVT archive use two project-file forms:

* JSON ``.wvproj`` files, which contain the complete buildConfig object;
* short binary/encrypted ``.wvproj`` files, whose usable build configuration is
  kept in the neighbouring ``.cproject`` and linked resources in ``.project``.

The latter is not decrypted or guessed.  The companion files are parsed and
the generated manifest records that fallback explicitly.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import platform
import re
import shlex
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


SOURCE_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".s", ".S", ".sx"}
SKIP_DIRECTORIES = {
    ".git",
    ".settings",
    ".metadata",
    ".mrs",
    "obj",
    "build",
    "out",
}


def clean_value(value: Any) -> str:
    """Turn MRS XML/JSON option values into a plain string."""

    if value is None:
        return ""
    text = html.unescape(str(value)).strip()
    while len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        text = text[1:-1].strip()
    return text


def bool_value(value: Any, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    return clean_value(value).lower() in {"1", "true", "yes", "on", "enabled"}


def suffix(value: Any) -> str:
    """Return the last meaningful part of an Eclipse enum value."""

    text = clean_value(value).rstrip(".")
    return text.rsplit(".", 1)[-1] if text else ""


def option_values(option: ET.Element | None) -> list[str]:
    if option is None:
        return []
    values: list[str] = []
    if "value" in option.attrib:
        values.append(clean_value(option.attrib["value"]))
    values.extend(clean_value(e.attrib.get("value")) for e in option.findall("listOptionValue"))
    return [value for value in values if value != ""]


def first_value(values: Iterable[str], default: str = "") -> str:
    for value in values:
        if value != "":
            return value
    return default


def find_option(parent: ET.Element, option_suffix: str, *, name: str | None = None) -> ET.Element | None:
    """Find the first option whose Eclipse superClass ends in option_suffix."""

    for option in parent.iter("option"):
        super_class = option.attrib.get("superClass", "")
        if not (super_class.endswith("." + option_suffix) or super_class.endswith(option_suffix)):
            continue
        if name is not None and option.attrib.get("name") != name:
            continue
        return option
    return None


def find_tool(parent: ET.Element, tool_suffix: str) -> ET.Element | None:
    for tool in parent.iter("tool"):
        super_class = tool.attrib.get("superClass", "")
        if super_class.endswith("." + tool_suffix) or super_class.endswith(tool_suffix):
            return tool
    return None


def tool_option_values(tool: ET.Element | None, option_suffix: str) -> list[str]:
    if tool is None:
        return []
    option = find_option(tool, option_suffix)
    return option_values(option)


def parse_raw_words(value: Any) -> list[str]:
    if isinstance(value, (list, tuple)):
        words: list[str] = []
        for item in value:
            words.extend(parse_raw_words(item))
        return words
    text = clean_value(value)
    if not text:
        return []
    try:
        return shlex.split(text)
    except ValueError:
        return text.split()


def parse_parent_location(project_dir: Path, location: str) -> Path:
    """Resolve Eclipse PARENT-N-PROJECT_LOC paths."""

    text = clean_value(location).replace("\\", "/")
    match = re.fullmatch(r"PARENT-(\d+)-PROJECT_LOC(?:/(.*))?", text)
    if match:
        count = int(match.group(1))
        base = project_dir.parents[count - 1] if count else project_dir
        tail = match.group(2) or ""
        return (base / tail).resolve()
    if text == "PROJECT_LOC":
        return project_dir.resolve()

    # Some EVT archives retain a Windows absolute path from the original
    # MRS workspace, for example ``E:/.../EXAM/SRC/Ld``.  When the same EVT
    # tree is moved to another host, recover the path relative to its local
    # ``EXAM`` directory instead of treating ``E:`` as a literal subfolder.
    exam_match = re.search(r"(?:^|/)EXAM/(.+)$", text, re.IGNORECASE)
    if exam_match:
        exam_dir = next((parent for parent in (project_dir, *project_dir.parents) if parent.name.lower() == "exam"), None)
        if exam_dir is not None:
            return (exam_dir / exam_match.group(1)).resolve()
    return (project_dir / text).resolve()


def parse_project_links(project_dir: Path) -> dict[str, Path]:
    """Read linked folders from Eclipse .project metadata."""

    result: dict[str, Path] = {}
    metadata = project_dir / ".project"
    if not metadata.exists():
        return result
    try:
        root = ET.parse(metadata).getroot()
    except ET.ParseError as exc:
        raise ValueError(f"cannot parse {metadata}: {exc}") from exc
    for link in root.findall("./linkedResources/link"):
        name = clean_value(link.findtext("name"))
        location = link.findtext("location") or link.findtext("locationURI") or ""
        if name and location:
            result[name] = parse_parent_location(project_dir, location)
    return result


def parse_cproject(cproject: Path, project_dir: Path) -> dict[str, Any]:
    """Parse the readable Eclipse/MRS build configuration."""

    try:
        root = ET.parse(cproject).getroot()
    except ET.ParseError as exc:
        raise ValueError(f"cannot parse {cproject}: {exc}") from exc

    configurations = list(root.iter("configuration"))
    configuration = next(
        (item for item in configurations if item.attrib.get("name", "").lower() in {"obj", "release"}),
        configurations[0] if configurations else None,
    )
    if configuration is None:
        raise ValueError(f"no build configuration found in {cproject}")
    toolchain = find_tool(configuration, "toolchain") or configuration

    def target_value(option_suffix: str, default: str = "") -> str:
        return first_value(option_values(find_option(toolchain, option_suffix)), default)

    def target_bool(option_suffix: str, default: bool = False) -> bool:
        return bool_value(target_value(option_suffix), default)

    assembler = find_tool(toolchain, "tool.assembler")
    ccompiler = find_tool(toolchain, "tool.c.compiler")
    cppcompiler = find_tool(toolchain, "tool.cpp.compiler")
    linker = find_tool(toolchain, "tool.c.linker")

    def tool_value(tool: ET.Element | None, option_suffix: str, default: str = "") -> str:
        return first_value(tool_option_values(tool, option_suffix), default)

    def tool_list(tool: ET.Element | None, option_suffix: str) -> list[str]:
        return tool_option_values(tool, option_suffix)

    target = {
        "architecture": suffix(target_value("target.isa.base", "rv32i")),
        "integer_ABI": suffix(target_value("target.abi.integer", "ilp32")),
        "multiply_extension": target_bool("target.isa.multiply"),
        "atomic_extension": target_bool("target.isa.atomic"),
        "compressed_extension": target_bool("target.isa.compressed"),
        "extra_compressed_extension": target_bool("target.isa.xw"),
        "bit_extension": target_bool("target.isa.b"),
        "zmmul": target_bool("target.isa.zmmul"),
        "floating_point": suffix(target_value("isa.fp", "none")),
        "floating_point_ABI": suffix(target_value("abi.fp", "none")),
        "save_restore": target_bool("target.saverestore"),
        "small_data_limit": target_value("target.smalldatalimit", "0"),
        "code_model": suffix(target_value("target.codemodel", "default")),
        "other_target_flags": target_value("target.other", ""),
    }

    optimization = {
        "level": suffix(tool_value(toolchain, "optimization.level", "none")),
        "message_length": target_bool("optimization.messagelength"),
        "char_is_signed": target_bool("optimization.signedchar"),
        "function_sections": target_bool("optimization.functionsections"),
        "data_sections": target_bool("optimization.datasections"),
        "no_common_unitialized": target_bool("optimization.nocommon"),
        "do_not_inline_functions": target_bool("optimization.noinlinefunctions"),
        "assume_freestanding_environment": target_bool("optimization.freestanding"),
        "disable_builtin": target_bool("optimization.nobuiltin"),
        "single_precision_constants": target_bool("optimization.singleprecisionconstant"),
        "position_independent_code": target_bool("optimization.pic"),
        "link_time_optimizer": target_bool("optimization.lto"),
        "other_optimization_flags": tool_value(toolchain, "optimization.other", ""),
    }

    warnings = {
        "warn_on_various_unused_elements": bool_value(tool_value(ccompiler, "warnings.unused")),
        "warn_on_uninitialized_variables": bool_value(tool_value(ccompiler, "warnings.uninitialized")),
        "enable_all_common_warnings": bool_value(tool_value(ccompiler, "warnings.all")),
        "enable_extra_warnings": bool_value(tool_value(ccompiler, "warnings.extra")),
        "other_warning_flags": tool_value(ccompiler, "warnings.other", ""),
    }

    debugging = {
        "debug_level": suffix(tool_value(toolchain, "debugging.level", "default")),
        "debug_format": suffix(tool_value(toolchain, "debugging.format", "default")),
        "other_debugging_flags": tool_value(toolchain, "debugging.other", ""),
    }

    assembler_config = {
        "preprocessor": {"use_preprocessor": bool_value(tool_value(assembler, "assembler.usepreprocessor", "true"))},
        "includes": {
            "include_paths": tool_list(assembler, "assembler.include.paths"),
            "include_system_paths": tool_list(assembler, "assembler.include.systempaths"),
            "include_files": tool_list(assembler, "assembler.include.files"),
        },
        "defined_symbols": tool_list(assembler, "assembler.defs"),
        "miscellaneous": {
            "assembler_flags": tool_list(assembler, "assembler.flags"),
            "other_assembler_flags": tool_value(assembler, "assembler.other", ""),
        },
    }

    ccompiler_config = {
        "preprocessor": {
            "defined_symbols": tool_list(ccompiler, "c.compiler.defs"),
            "undefined_symbols": tool_list(ccompiler, "c.compiler.undefs"),
            "do_not_search_system_directories": bool_value(tool_value(ccompiler, "c.compiler.nostdinc")),
        },
        "includes": {
            "include_paths": tool_list(ccompiler, "c.compiler.include.paths"),
            "include_system_paths": tool_list(ccompiler, "c.compiler.include.systempaths"),
            "include_files": tool_list(ccompiler, "c.compiler.include.files"),
        },
        "optimization": {
            "language_standard": suffix(tool_value(ccompiler, "c.compiler.std", "gnu99")),
            "other_optimization_flags": tool_value(ccompiler, "c.compiler.other", ""),
        },
        "miscellaneous": {"other_compiler_flags": tool_value(ccompiler, "c.compiler.other", "")},
    }

    linker_config = {
        "general": {
            "scriptFiles": tool_list(linker, "c.linker.scriptfile"),
            "do_not_use_standard_start_files": bool_value(tool_value(linker, "c.linker.nostart")),
            "do_not_use_default_libraries": bool_value(tool_value(linker, "c.linker.nodeflibs")),
            "no_startup_or_default_libs": bool_value(tool_value(linker, "c.linker.nostdlibs")),
            "remove_unused_sections": bool_value(tool_value(linker, "c.linker.gcsections")),
            "print_removed_sections": bool_value(tool_value(linker, "c.linker.printgcsections")),
        },
        "libraries": {
            "libraries": tool_list(linker, "c.linker.libs"),
            "library_search_path": tool_list(linker, "c.linker.paths"),
        },
        "miscellaneous": {
            "linker_flags": tool_list(linker, "c.linker.flags"),
            "other_objects": tool_list(linker, "c.linker.otherobjs"),
            "generate_map": tool_value(linker, "c.linker.mapfilename", ""),
            "cross_reference": bool_value(tool_value(linker, "c.linker.cref")),
            "print_link_map": bool_value(tool_value(linker, "c.linker.printmap")),
            "use_newlib_nano": bool_value(tool_value(linker, "c.linker.usenewlibnano")),
            "use_float_with_nano_printf": bool_value(tool_value(linker, "c.linker.useprintffloat")),
            "use_float_with_nano_scanf": bool_value(tool_value(linker, "c.linker.usescanffloat")),
            "do_not_use_syscalls": bool_value(tool_value(linker, "c.linker.usenewlibnosys")),
            "use_wch_printf": bool_value(tool_value(linker, "c.linker.printf")),
            "use_wch_printffloat": bool_value(tool_value(linker, "c.linker.printfloat")),
            "use_iqmath": bool_value(tool_value(linker, "c.linker.iqmath")),
            "other_linker_flags": tool_value(linker, "c.linker.other", ""),
        },
    }

    source_entries = []
    for entry in configuration.iter("entry"):
        if entry.attrib.get("kind") != "sourcePath":
            continue
        source_entries.append(
            {
                "name": clean_value(entry.attrib.get("name", "")),
                "excluding": [x for x in clean_value(entry.attrib.get("excluding", "")).split("|") if x],
            }
        )

    prefix = first_value(option_values(find_option(toolchain, "command.prefix")), "")
    compiler_option = first_value(option_values(find_option(toolchain, "target.rvGcc")), "")
    compiler_match = re.search(r"\.(\d+)$", compiler_option)
    compiler_major = int(compiler_match.group(1)) if compiler_match else None
    if compiler_major is None:
        if prefix.startswith("riscv-none-"):
            compiler_major = 8
        elif prefix.startswith("riscv32-wch"):
            compiler_major = 15

    return {
        "project_name": project_dir.name,
        "artifact_name": project_dir.name,
        "artifact_extension": "elf",
        "target": target,
        "toolchain_major": compiler_major,
        "toolchain_prefix_hint": prefix,
        "component_toolchain": "",
        "optimization": optimization,
        "warnings": warnings,
        "debugging": debugging,
        "assembler": assembler_config,
        "ccompiler": ccompiler_config,
        "clinker": linker_config,
        "createFlash": {"enabled": True, "outputFileFormat": "ihex"},
        "createList": {"enabled": True, "disassemble": True},
        "printSize": {"enabled": True},
        "exclude_resources": [],
        "source_entries": source_entries,
        "format": "cproject-fallback",
    }


def parse_json_wvproj(data: dict[str, Any], project_dir: Path) -> dict[str, Any]:
    basic = data.get("basic", {})
    build = data.get("buildConfig", {})
    configurations = build.get("configurations", [])
    if not configurations:
        raise ValueError("wvproj has no buildConfig.configurations")
    config = next((item for item in configurations if item.get("name") == "obj"), configurations[0])
    target = dict(config.get("riscvTargetProcessor", {}))
    component = clean_value(config.get("component_toolchain", ""))
    match = re.search(r"GCC(\d+)", component, re.IGNORECASE)
    compiler_major = int(match.group(1)) if match else None
    artifact = config.get("buildArtifact", {})
    project_name = clean_value(basic.get("projectName")) or project_dir.name
    artifact_name = clean_value(artifact.get("artifact_name")) or project_name
    artifact_name = artifact_name.replace("${ProjName}", project_name).replace("${BuildArtifactFileBaseName}", project_name)
    return {
        "project_name": project_name,
        "artifact_name": artifact_name,
        "artifact_extension": clean_value(artifact.get("artifact_extension")) or "elf",
        "target": target,
        "toolchain_major": compiler_major,
        "toolchain_prefix_hint": "",
        "component_toolchain": component,
        "optimization": config.get("optimization", {}),
        "warnings": config.get("warnings", {}),
        "debugging": config.get("debugging", {}),
        "assembler": config.get("assembler", {}),
        "ccompiler": config.get("ccompiler", {}),
        "clinker": config.get("clinker", {}),
        "createFlash": config.get("createFlash", {}),
        "createList": config.get("createList", {}),
        "printSize": config.get("printSize", {}),
        "exclude_resources": config.get("excludeResources", []),
        "source_entries": [],
        "linked_folders": basic.get("linkedFolders", []),
        "format": "json",
    }


def load_project(wvproj: Path) -> dict[str, Any]:
    wvproj = wvproj.resolve()
    if not wvproj.is_file():
        raise ValueError(f"input is not a file: {wvproj}")
    project_dir = wvproj.parent
    raw = wvproj.read_bytes()
    try:
        data = json.loads(raw.decode("utf-8-sig"))
        if not isinstance(data, dict):
            raise ValueError("top-level JSON is not an object")
        config = parse_json_wvproj(data, project_dir)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        cproject = project_dir / ".cproject"
        if not cproject.exists():
            raise ValueError(
                f"{wvproj} is not readable JSON and has no companion .cproject; "
                "the encrypted MRS format cannot be converted without its metadata"
            )
        config = parse_cproject(cproject, project_dir)
        config["encrypted_wvproj"] = True
        config["companion_cproject"] = str(cproject)

    config["wvproj"] = str(wvproj)
    config["project_dir"] = str(project_dir)
    config["companion_project"] = str(project_dir / ".project") if (project_dir / ".project").exists() else ""

    # Always use Eclipse source entries when available.  JSON wvproj files do
    # not repeat those exclusions, while .cproject contains the exact MRS
    # source-root selection.
    cproject = project_dir / ".cproject"
    cproject_config: dict[str, Any] | None = None
    if cproject.exists():
        cproject_config = parse_cproject(cproject, project_dir)
        if not config.get("source_entries"):
            config["source_entries"] = cproject_config.get("source_entries", [])
        config["cproject_format"] = cproject_config.get("format")

    links = parse_project_links(project_dir)
    for item in config.get("linked_folders", []):
        name = clean_value(item.get("name"))
        location = clean_value(item.get("location"))
        if name and location:
            links.setdefault(name, (project_dir / location).resolve())
    config["linked_folders_resolved"] = {name: str(path) for name, path in sorted(links.items())}

    # A few JSON projects contain a stale default ``${project}/Ld/Link.ld``
    # while their companion .cproject names the actual project-specific
    # linker script.  Preserve the JSON configuration when it resolves, but
    # use the readable MRS metadata when every JSON script is missing.
    if cproject_config is not None and config.get("format") == "json":
        json_scripts = config.get("clinker", {}).get("general", {}).get("scriptFiles", [])
        cproject_scripts = cproject_config.get("clinker", {}).get("general", {}).get("scriptFiles", [])
        json_script_paths = [resolve_path(value, config) for value in json_scripts]
        if cproject_scripts and json_script_paths and not any(path.exists() for path in json_script_paths):
            config["clinker"] = cproject_config.get("clinker", {})
            config["linker_config_fallback"] = True
    return config


def resolve_path(value: Any, config: dict[str, Any]) -> Path:
    """Resolve MRS ${project}/${workspace_loc} paths and linked folders."""

    text = clean_value(value).replace("\\", "/")
    project_dir = Path(config["project_dir"])
    links = {name: Path(path) for name, path in config.get("linked_folders_resolved", {}).items()}

    workspace_pattern = re.fullmatch(r"\$\{workspace_loc:/\$\{ProjName\}(?:/(.*))?\}", text)
    if workspace_pattern:
        text = workspace_pattern.group(1) or ""
    else:
        # Be permissive for the non-nested spelling emitted by some Eclipse
        # versions: ${workspace_loc:/ProjectName/path}.
        workspace_pattern = re.fullmatch(r"\$\{workspace_loc:/[^/}]+(?:/(.*))?\}", text)
        if workspace_pattern:
            text = workspace_pattern.group(1) or ""
    text = text.replace("${project}/", "").replace("${project}", "")
    text = text.replace("${ProjName}/", "").replace("${ProjName}", "")
    text = text.lstrip("/")

    parts = PurePosixPath(text).parts
    if parts and parts[0] in links:
        return (links[parts[0]] / Path(*parts[1:])).resolve()
    candidate = (project_dir / Path(text)).resolve()
    if not candidate.exists() and text.startswith("../"):
        # Some older MRS projects store an include such as ``../User`` even
        # though the directory is project-local.  Prefer the existing local
        # spelling when the literal parent-relative path is stale.
        local_text = text
        while local_text.startswith("../"):
            local_text = local_text[3:]
        local_candidate = (project_dir / Path(local_text)).resolve()
        if local_candidate.exists():
            return local_candidate
    return candidate


def path_is_excluded(relative: str, patterns: Iterable[str]) -> bool:
    rel = PurePosixPath(relative.replace(os.sep, "/"))
    for pattern in patterns:
        p = PurePosixPath(clean_value(pattern).replace("\\", "/")).relative_to(".") if clean_value(pattern).startswith("./") else PurePosixPath(clean_value(pattern).replace("\\", "/"))
        if str(rel) == str(p) or str(rel).startswith(str(p).rstrip("/") + "/"):
            return True
    return False


def collect_sources(config: dict[str, Any]) -> tuple[list[Path], list[str]]:
    project_dir = Path(config["project_dir"])
    links = {name: Path(path) for name, path in config.get("linked_folders_resolved", {}).items()}
    entry_excludes: dict[str, list[str]] = {}
    for entry in config.get("source_entries", []):
        name = clean_value(entry.get("name", ""))
        values = entry_excludes.setdefault(name, [])
        for item in entry.get("excluding", []):
            text = clean_value(item).replace("\\", "/")
            if text and text not in values:
                values.append(text)

    roots: list[tuple[str, Path]] = [("", project_dir)]
    roots.extend(sorted(links.items()))
    linked_names = set(links)
    local_entry_names = sorted(name for name in entry_excludes if name and name not in linked_names)
    roots.extend((name, project_dir / Path(name)) for name in local_entry_names)
    global_excludes: list[str] = []
    for item in config.get("exclude_resources", []):
        text = clean_value(item).replace("\\", "/")
        text = text.replace("${project}/", "").replace("${project}", "").lstrip("/")
        global_excludes.append(text)

    def root_excludes(logical_name: str) -> list[str]:
        """Translate project-relative exclusions to a linked-root-relative path."""

        excludes = [clean_value(item).replace("\\", "/") for item in entry_excludes.get(logical_name, [])]
        if not logical_name:
            return excludes
        prefix = logical_name.rstrip("/") + "/"
        for item in entry_excludes.get("", []):
            text = clean_value(item).replace("\\", "/")
            if text.startswith(prefix):
                excludes.append(text[len(prefix):])
        return excludes

    def linked_global_excludes(logical_name: str) -> list[str]:
        if not logical_name:
            return list(global_excludes)
        prefix = logical_name.rstrip("/") + "/"
        return [item[len(prefix):] for item in global_excludes if item.startswith(prefix)]

    sources: dict[Path, None] = {}
    source_fingerprints: set[tuple[int, bytes]] = set()
    warnings: list[str] = []
    for logical_name, root in roots:
        if not root.exists():
            warnings.append(f"linked source root does not exist: {logical_name} -> {root}")
            continue
        excludes = root_excludes(logical_name)
        excludes.extend(linked_global_excludes(logical_name))
        for candidate in root.rglob("*"):
            if not candidate.is_file() or candidate.suffix not in SOURCE_SUFFIXES:
                continue
            try:
                rel = candidate.relative_to(root).as_posix()
            except ValueError:
                rel = candidate.name
            try:
                project_rel = candidate.relative_to(project_dir).as_posix()
            except ValueError:
                project_rel = ""
            if any(part in SKIP_DIRECTORIES for part in candidate.relative_to(root).parts):
                continue
            excluded = path_is_excluded(rel, excludes)
            if not excluded and project_rel and not logical_name:
                excluded = path_is_excluded(project_rel, global_excludes)
            # For project-local source roots, Eclipse names subdirectories as
            # source entries (for example APP, Profile, or Debug).  Apply the
            # corresponding entry exclusion to the path below that directory.
            # Linked roots already receive their named entry exclusions above.
            if not excluded and not logical_name:
                project_parts = PurePosixPath(rel).parts
                if project_parts and project_parts[0] in local_entry_names:
                    excluded = True
                elif len(project_parts) > 1 and project_parts[0] in entry_excludes:
                    excluded = path_is_excluded(
                        "/".join(project_parts[1:]), entry_excludes[project_parts[0]]
                    )
            if excluded:
                continue
            resolved = candidate.resolve()
            try:
                stat = resolved.stat()
                fingerprint = (stat.st_size, hashlib.sha256(resolved.read_bytes()).digest())
            except OSError:
                fingerprint = None
            # EVT archives sometimes expose the same source once as a local
            # file and once through a linked shared directory.  Compiling
            # both copies creates duplicate symbols; retain the first copy,
            # which follows Eclipse's project-root-first ordering.
            if fingerprint is not None and fingerprint in source_fingerprints:
                continue
            if fingerprint is not None:
                source_fingerprints.add(fingerprint)
            sources[resolved] = None

    if not sources:
        raise ValueError(f"no C/assembly sources found for {config['wvproj']}")
    return sorted(sources), warnings


def target_flags(config: dict[str, Any], gcc_major: int | None = None) -> tuple[str, str, list[str]]:
    """Build the ``-march``/``-mabi`` pair and the remaining target options.

    ``gcc_major`` selects the ``-march`` dialect: MounRiver spells the ISA
    string differently for its GCC 8 component toolchain than for GCC 12/15.
    ``None`` keeps the modern GCC 12/15 dialect.
    """

    target = config.get("target", {})
    arch = clean_value(target.get("architecture", "rv32i")).lower()
    arch = arch if arch.startswith("rv32") else "rv32i"
    base = arch
    if base not in {"rv32e", "rv32i"} and base.startswith("rv32"):
        # A few MRS files store a complete base string.  Keep its standard
        # single-letter portion and append the structured options below.
        base = re.match(r"rv32[ie][imafdc]", base).group(0) if re.match(r"rv32[ie][imafdc]", base) else "rv32i"

    def enabled(key: str) -> bool:
        return bool_value(target.get(key))

    letters = ""
    for letter, key in (("m", "multiply_extension"), ("a", "atomic_extension")):
        if enabled(key) and letter not in base[4:]:
            letters += letter
    fp = suffix(target.get("floating_point", "none"))
    if fp in {"single", "f"} and "f" not in base[4:] and "f" not in letters:
        letters += "f"
    if enabled("compressed_extension") and "c" not in base[4:] and "c" not in letters:
        letters += "c"
    march = base + letters

    extensions: list[str] = []
    if gcc_major is not None and gcc_major < 12:
        # MounRiver keeps a separate -march dialect for its GCC 8 component
        # toolchain: the base string is shared, but the only extension it ever
        # appends is a bare ``xw`` -- GCC 8 rejects every ``_``-separated
        # spelling of it.  The B components, Zmmul and the vector-crypto set
        # are dropped rather than spelled out, because GCC 8 has no accepted
        # spelling for them at all.
        if enabled("extra_compressed_extension"):
            march += "xw"
    else:
        if enabled("bit_extension"):
            # MRS GCC12 and GCC15 both accept the explicit B components; GCC12
            # does not accept the shorthand `_b` spelling.
            extensions.extend(["zba", "zbb", "zbc", "zbs"])
        if enabled("zmmul") and not enabled("multiply_extension"):
            extensions.append("zmmul")
        if enabled("extra_compressed_extension"):
            extensions.append("xw")
        vector = clean_value(target.get("vector_cryptography_extensions", ""))
        if vector:
            extensions.extend(x for x in re.split(r"[,_ ]+", vector) if x.startswith("z"))
    if extensions:
        march += "_" + "_".join(dict.fromkeys(extensions))

    abi = suffix(target.get("floating_point_ABI", "none"))
    integer_abi = suffix(target.get("integer_ABI", "ilp32")) or "ilp32"
    if abi in {"single", "f"}:
        abi = "ilp32f" if integer_abi == "ilp32" else integer_abi + "f"
    elif abi in {"double", "d"}:
        abi = "ilp32d" if integer_abi == "ilp32" else integer_abi + "d"
    else:
        abi = integer_abi

    flags: list[str] = [f"-march={march}", f"-mabi={abi}"]
    if enabled("save_restore"):
        flags.append("-msave-restore")
    small_data = clean_value(target.get("small_data_limit", ""))
    if small_data and small_data not in {"0", "default"}:
        flags.append(f"-msmall-data-limit={small_data}")
    code_model = suffix(target.get("code_model", "default"))
    if code_model in {"any", "medany"}:
        flags.append("-mcmodel=medany")
    elif code_model in {"low", "medlow"}:
        flags.append("-mcmodel=medlow")
    flags.extend(parse_raw_words(target.get("other_target_flags", "")))
    return march, abi, flags


def config_flags(config: dict[str, Any], gcc_major: int | None = None) -> dict[str, list[str]]:
    opt = config.get("optimization", {})
    warning = config.get("warnings", {})
    debug = config.get("debugging", {})
    ccompiler = config.get("ccompiler", {})
    assembler = config.get("assembler", {})
    compiler_pre = ccompiler.get("preprocessor", {})
    compiler_inc = ccompiler.get("includes", {})
    asm_pre = assembler.get("preprocessor", {})
    asm_inc = assembler.get("includes", {})

    target_march, target_abi, target = target_flags(config, gcc_major)
    cflags: list[str] = []
    level = suffix(opt.get("level", ""))
    level_map = {"none": "-O0", "size": "-Os", "speed": "-O3", "fast": "-Ofast", "debug": "-Og"}
    if level in level_map:
        cflags.append(level_map[level])
    elif level.startswith("o") and level[1:].isdigit():
        cflags.append("-" + level)
    if bool_value(opt.get("message_length")):
        cflags.append("-fmessage-length=0")
    for key, flag in (
        ("char_is_signed", "-fsigned-char"),
        ("function_sections", "-ffunction-sections"),
        ("data_sections", "-fdata-sections"),
        ("no_common_unitialized", "-fno-common"),
        ("do_not_inline_functions", "-fno-inline-functions"),
        ("assume_freestanding_environment", "-ffreestanding"),
        ("disable_builtin", "-fno-builtin"),
        ("single_precision_constants", "-fsingle-precision-constant"),
        ("position_independent_code", "-fpic"),
        ("link_time_optimizer", "-flto"),
    ):
        if bool_value(opt.get(key)):
            cflags.append(flag)
    # GCC 8 (used by many V2/V3/V4 EVT projects) defaults to common tentative
    # definitions.  GCC 10+ changed that default, so preserve the project
    # toolchain's behaviour when an older project does not explicitly request
    # ``-fno-common``.
    requested_toolchain = normalized_toolchain_major(config)
    if requested_toolchain is not None and requested_toolchain < 10 and not bool_value(opt.get("no_common_unitialized")):
        cflags.append("-fcommon")
    if requested_toolchain is not None and requested_toolchain < 14:
        # GCC 15 diagnoses a few legacy EVT pointer conversions as errors;
        # the projects declare older GCC toolchains where these were warnings.
        cflags.append("-Wno-error=incompatible-pointer-types")
    cflags.extend(parse_raw_words(opt.get("other_optimization_flags", "")))

    language = suffix(ccompiler.get("optimization", {}).get("language_standard", "gnu99"))
    if language:
        cflags.append("-std=" + language)
    cflags.extend(parse_raw_words(ccompiler.get("optimization", {}).get("other_optimization_flags", "")))
    for key, flag in (
        ("warn_on_various_unused_elements", "-Wunused"),
        ("warn_on_uninitialized_variables", "-Wuninitialized"),
        ("enable_all_common_warnings", "-Wall"),
        ("enable_extra_warnings", "-Wextra"),
    ):
        if bool_value(warning.get(key)):
            cflags.append(flag)
    cflags.extend(parse_raw_words(warning.get("other_warning_flags", "")))

    debug_level = suffix(debug.get("debug_level", "default"))
    if debug_level not in {"", "default", "none"}:
        cflags.append("-g")
    debug_format = suffix(debug.get("debug_format", "default"))
    if debug_format.startswith("dwarf") and debug_format[5:].isdigit():
        # GCC 15 no longer accepts the old ``-gdwarf4`` spelling.
        # The hyphenated form is accepted by the older WCH toolchains too.
        cflags.append("-gdwarf-" + debug_format[5:])
    cflags.extend(parse_raw_words(debug.get("other_debugging_flags", "")))

    cppflags: list[str] = []
    for value in compiler_pre.get("defined_symbols", []) or []:
        cppflags.append("-D" + clean_value(value))
    for value in compiler_pre.get("undefined_symbols", []) or []:
        cppflags.append("-U" + clean_value(value))
    if bool_value(compiler_pre.get("do_not_search_system_directories")):
        cppflags.append("-nostdinc")
    for value in compiler_inc.get("include_paths", []) or []:
        cppflags.append("-I" + "@@PATH@@" + clean_value(value))
    for value in compiler_inc.get("include_system_paths", []) or []:
        cppflags.append("-isystem" + "@@PATH@@" + clean_value(value))
    for value in compiler_inc.get("include_files", []) or []:
        cppflags.append("-include" + "@@PATH@@" + clean_value(value))

    asflags: list[str] = []
    if bool_value(asm_pre.get("use_preprocessor"), True):
        asflags.append("-x")
        asflags.append("assembler-with-cpp")
    for value in asm_pre.get("defined_symbols", []) or []:
        asflags.append("-D" + clean_value(value))
    for value in asm_inc.get("include_paths", []) or []:
        asflags.append("-I" + "@@PATH@@" + clean_value(value))
    for value in asm_inc.get("include_system_paths", []) or []:
        asflags.append("-isystem" + "@@PATH@@" + clean_value(value))
    for value in asm_inc.get("include_files", []) or []:
        asflags.append("-include" + "@@PATH@@" + clean_value(value))
    misc_asm = assembler.get("miscellaneous", {})
    asflags.extend(parse_raw_words(misc_asm.get("assembler_flags", [])))
    asflags.extend(parse_raw_words(misc_asm.get("other_assembler_flags", "")))

    return {
        "target": target,
        "march": [target_march],
        "abi": [target_abi],
        "cflags": cflags,
        "cppflags": cppflags,
        "asflags": asflags,
    }


def resolve_flag_paths(flags: list[str], config: dict[str, Any]) -> list[str]:
    result: list[str] = []
    for flag in flags:
        if "@@PATH@@" not in flag:
            result.append(flag)
            continue
        prefix, value = flag.split("@@PATH@@", 1)
        result.append(prefix + str(resolve_path(value, config)))
    return result


def linker_flags(config: dict[str, Any], output_dir: Path, artifact: str) -> tuple[list[str], list[str], list[Path]]:
    linker = config.get("clinker", {})
    general = linker.get("general", {})
    libraries = linker.get("libraries", {})
    misc = linker.get("miscellaneous", {})
    scripts: list[Path] = []
    for value in general.get("scriptFiles", []) or []:
        path = resolve_path(value, config)
        if path.exists() and path not in scripts:
            scripts.append(path)
    if not scripts:
        raise ValueError(f"no existing linker script found for {config['wvproj']}")

    flags: list[str] = []
    for path in scripts:
        flags.append("-T" + str(path))
    if bool_value(general.get("do_not_use_standard_start_files")):
        flags.append("-nostartfiles")
    if bool_value(general.get("do_not_use_default_libraries")):
        flags.append("-nodefaultlibs")
    if bool_value(general.get("no_startup_or_default_libs")):
        flags.append("-nostdlib")
    if bool_value(general.get("remove_unused_sections")):
        flags.append("-Wl,--gc-sections")
    if bool_value(general.get("print_removed_sections")):
        flags.append("-Wl,--print-gc-sections")
    if bool_value(misc.get("cross_reference")):
        flags.append("-Wl,--cref")
    if bool_value(misc.get("print_link_map")):
        flags.append("-Wl,-Map," + str(output_dir / (artifact + ".map")))
    if bool_value(misc.get("generate_map")) or clean_value(misc.get("generate_map")):
        if not any("-Map," in item for item in flags):
            flags.append("-Wl,-Map," + str(output_dir / (artifact + ".map")))
    if bool_value(misc.get("use_newlib_nano")):
        flags.append("--specs=nano.specs")
    if bool_value(misc.get("do_not_use_syscalls")):
        flags.append("--specs=nosys.specs")
    if bool_value(misc.get("use_float_with_nano_printf")):
        flags.append("-u"); flags.append("_printf_float")
    if bool_value(misc.get("use_float_with_nano_scanf")):
        flags.append("-u"); flags.append("_scanf_float")
    if bool_value(misc.get("use_wch_printf")):
        flags.append("-lprintf")
    if bool_value(misc.get("use_wch_printffloat")):
        flags.append("-lprintfloat")
    if bool_value(misc.get("use_iqmath")):
        flags.append("-lIQmath_RV32")
    for value in libraries.get("library_search_path", []) or []:
        path = resolve_path(value, config)
        if path.exists():
            flags.append("-L" + str(path))
    for value in libraries.get("libraries", []) or []:
        library = clean_value(value)
        if library:
            flags.append(library if library.startswith("-l") else "-l" + library)
    raw_flags: list[str] = []
    for value in misc.get("linker_flags", []) or []:
        text = clean_value(value)
        if text.startswith("-Wl,"):
            raw_flags.append(text)
        elif text.startswith("-Xlinker"):
            raw_flags.extend(parse_raw_words(text))
        elif text:
            raw_flags.append("-Wl," + text)
    raw_flags.extend(parse_raw_words(misc.get("other_linker_flags", "")))
    flags.extend(raw_flags)
    objects = [resolve_path(value, config) for value in misc.get("other_objects", []) or []]
    objects = [path for path in objects if path.exists()]
    return flags, [str(path) for path in objects], scripts


def make_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("$", "$$").replace("#", "\\#").replace(" ", "\\ ").replace("\t", "\\\t")


def make_words(values: Iterable[str]) -> str:
    return " ".join(make_escape(str(value)) for value in values)


def select_toolchain(
    config: dict[str, Any],
    gcc_root: Path,
    host_platform: str,
    requested_major: int | None,
    explicit_major: bool = False,
) -> dict[str, str | int | bool]:
    platform_dir = gcc_root / host_platform
    if not platform_dir.is_dir():
        raise ValueError(f"toolchain platform directory does not exist: {platform_dir}")
    versions = []
    for item in platform_dir.iterdir():
        if not item.is_dir():
            continue
        match = re.match(r"^(\d+)\.(\d+)(?:\.(\d+))?$", item.name)
        if match:
            versions.append((int(match.group(1)), int(match.group(2)), int(match.group(3) or 0), item))
    if not versions:
        raise ValueError(f"no versioned GCC toolchain found under {platform_dir}")
    # GCC 8, which is still used by several legacy MRS projects, predates
    # the WCH ``xw`` extension and the Zb/Zmmul extensions.  Prefer the
    # oldest installed compiler that can parse those ISA strings when the
    # project metadata asks for an older compiler.
    # Probe the modern GCC 12/15 dialect on purpose: the question here is
    # whether the project's ISA request needs a compiler that speaks it.
    march, _abi, _target_flags = target_flags(config)
    needs_modern_isa = any(
        extension in march
        for extension in ("_xw", "_zba", "_zbb", "_zbc", "_zbs", "_zmmul")
    )
    minimum_major = 12 if needs_modern_isa else 0

    chosen = None
    compatibility_upgrade = False
    if requested_major is not None:
        matches = [item for item in versions if item[0] == requested_major]
        # An explicit ``--gcc-major`` is a direct instruction and is never
        # substituted: the generated ``-march`` follows the selected compiler's
        # own dialect (see target_flags), so an older compiler is handed the
        # spelling it accepts instead of being swapped for a newer one.  The
        # ISA gate stays in force for a major inferred from project metadata.
        if matches and (explicit_major or requested_major >= minimum_major):
            chosen = sorted(matches)[-1]
        elif matches and minimum_major:
            compatible = [item for item in versions if item[0] >= minimum_major]
            if compatible:
                chosen = sorted(compatible)[0]
                compatibility_upgrade = True
    if chosen is None:
        chosen = sorted(versions)[-1]
    major, _minor, _patch, root = chosen
    prefixes = [
        "riscv32-wch-elf-",
        "riscv-wch-elf-",
        "riscv-none-embed-",
        "riscv-none-elf-",
    ]
    prefix = next((candidate for candidate in prefixes if (root / "bin" / (candidate + "gcc")).exists()), None)
    if prefix is None:
        raise ValueError(f"no supported RISC-V GCC prefix found under {root / 'bin'}")
    return {
        "platform": host_platform,
        "root": str(root.resolve()),
        "bin": str((root / "bin").resolve()),
        "prefix": prefix,
        "compiler": str((root / "bin" / (prefix + "gcc")).resolve()),
        "version": f"{major}.{_minor}.{_patch}",
        "requested_major": requested_major if requested_major is not None else "",
        "fallback": requested_major is not None and major != requested_major,
        "compatibility_upgrade": compatibility_upgrade,
        "minimum_major": minimum_major,
    }


def probe_compiler_major(compiler: Path) -> tuple[int | None, str]:
    """Ask a compiler for its own major version via ``-dumpversion``.

    Used for compilers outside the versioned ``ref/gcc`` tree, whose directory
    layout carries no version.  Returns ``(major, warning)``; ``major`` is
    ``None`` when the probe fails, and the caller then keeps the modern
    GCC 12/15 ``-march`` dialect.
    """

    try:
        result = subprocess.run(
            [str(compiler), "-dumpversion"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"could not run '{compiler} -dumpversion' ({exc}); kept the GCC 12/15 -march dialect"
    lines = result.stdout.strip().splitlines()
    match = re.match(r"\s*(\d+)", lines[0]) if result.returncode == 0 and lines else None
    if match is None:
        return None, f"'{compiler} -dumpversion' reported no usable version; kept the GCC 12/15 -march dialect"
    return int(match.group(1)), ""


def select_explicit_compiler(config: dict[str, Any], compiler_path: Path) -> dict[str, str | int | bool]:
    """Use an explicitly supplied GCC executable without platform selection."""

    compiler = compiler_path.expanduser().resolve()
    if not compiler.is_file():
        raise ValueError(f"compiler path does not exist or is not a file: {compiler}")
    if not os.access(compiler, os.X_OK):
        raise ValueError(f"compiler path is not executable: {compiler}")

    name = compiler.name
    if name.endswith(".exe"):
        name = name[:-4]
    if not name.endswith("gcc"):
        raise ValueError(f"compiler path must name a GCC executable ending in 'gcc': {compiler}")
    prefix = name[:-3]
    bin_dir = compiler.parent
    root = bin_dir.parent if bin_dir.name == "bin" else bin_dir

    version = root.name if re.fullmatch(r"\d+\.\d+(?:\.\d+)?", root.name) else "explicit"
    platform_name = next((item for item in ("darwin-arm64", "linux-amd64") if item in compiler.parts), "explicit")
    version_parts = version.split(".") if version != "explicit" else []
    major = int(version_parts[0]) if version_parts else ""
    probed_major: int | None = None
    probe_warning = ""
    if version == "explicit":
        # The compiler sits outside the versioned ref/gcc tree, so its path
        # carries no version.  Ask the compiler itself: the -march dialect has
        # to follow the compiler that will actually run, exactly as MounRiver
        # branches on its component toolchain's real version.  Without this the
        # same project converts differently depending only on where the
        # compiler is installed, so a golden-vs-candidate comparison that swaps
        # one build for another can never match.
        probed_major, probe_warning = probe_compiler_major(compiler)
    # Modern-dialect probe, as in select_toolchain: this records what the
    # project asks for, not what the explicitly named compiler will be given.
    _march, _abi, target_flags_for_compiler = target_flags(config)
    needs_modern_isa = any(
        extension in " ".join(target_flags_for_compiler)
        for extension in ("_xw", "_zba", "_zbb", "_zbc", "_zbs", "_zmmul")
    )
    toolchain: dict[str, str | int | bool] = {
        "platform": platform_name,
        "selection": "explicit-compiler",
        "root": str(root),
        "bin": str(bin_dir),
        "prefix": prefix,
        "compiler": str(compiler),
        "version": version,
        "requested_major": normalized_toolchain_major(config) or "",
        "fallback": False,
        "compatibility_upgrade": False,
        "minimum_major": 12 if needs_modern_isa else 0,
        "explicit_compiler": True,
    }
    # Recorded only when the probe actually ran, so a compiler inside the
    # versioned tree keeps producing exactly the manifest it produced before.
    if probed_major is not None:
        toolchain["probed_major"] = probed_major
    if probe_warning:
        toolchain["version_probe_warning"] = probe_warning
    return toolchain


def normalized_toolchain_major(config: dict[str, Any]) -> int | None:
    value = config.get("toolchain_major")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    component = clean_value(config.get("component_toolchain", ""))
    match = re.search(r"GCC(\d+)", component, re.IGNORECASE)
    return int(match.group(1)) if match else None


def toolchain_march_major(toolchain: dict[str, Any]) -> int | None:
    """Major version of the selected toolchain, for the ``-march`` dialect.

    The version carried by the ``ref/gcc`` directory layout wins; for a
    compiler outside that tree the major probed from the compiler itself is
    used instead (see probe_compiler_major).  ``None`` -- neither available --
    keeps the modern GCC 12/15 dialect.
    """

    match = re.match(r"^(\d+)\.", str(toolchain.get("version", "")))
    if match:
        return int(match.group(1))
    probed = toolchain.get("probed_major")
    return probed if isinstance(probed, int) else None


def detect_platform() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    if system == "darwin" and machine in {"arm64", "aarch64"}:
        return "darwin-arm64"
    if system == "linux" and machine in {"x86_64", "amd64"}:
        return "linux-amd64"
    raise ValueError(f"unsupported host platform {system}/{machine}; expected darwin-arm64 or linux-amd64")


def build_makefile(config: dict[str, Any], output_dir: Path, toolchain: dict[str, Any], sources: list[Path], source_warnings: list[str]) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = re.sub(r"[^A-Za-z0-9_.-]+", "_", clean_value(config.get("artifact_name")) or Path(config["project_dir"]).name)
    config["artifact_name_resolved"] = artifact

    flags = config_flags(config, toolchain_march_major(toolchain))
    cppflags = resolve_flag_paths(flags["cppflags"], config)
    asflags = resolve_flag_paths(flags["asflags"], config)
    # The generated Makefile keeps all products below its own obj/ directory.
    # Use that default location when materialising the MRS map-file option.
    ldflags, other_objects, scripts = linker_flags(config, output_dir / "obj", artifact)
    # Static libraries must follow the object files on the link command line;
    # otherwise GNU ld sees no unresolved references yet and does not extract
    # the needed members.  Keep search paths/options in LDFLAGS and append all
    # ``-l`` options to the trailing LDLIBS list.
    trailing_libraries = [flag for flag in ldflags if flag.startswith("-l")]
    ldflags = [flag for flag in ldflags if not flag.startswith("-l")]
    other_objects = other_objects + trailing_libraries
    source_objects: list[tuple[Path, str]] = []
    for index, source in enumerate(sources):
        suffix_name = source.suffix.lower().lstrip(".") or "src"
        stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", source.stem)
        object_name = f"{index:04d}_{stem}.{suffix_name}.o"
        source_objects.append((source, str(Path("obj") / object_name)))
    objects = [obj for _source, obj in source_objects]
    depfiles = [str(Path(obj).with_suffix(".d")) for obj in objects]

    flash = config.get("createFlash", {})
    flash_enabled = bool_value(flash.get("enabled"), False)
    flash_format = suffix(flash.get("outputFileFormat", "ihex"))
    list_config = config.get("createList", {})
    list_enabled = bool_value(list_config.get("enabled"), False)
    hex_target = f"$(BUILD_DIR)/{artifact}.hex" if flash_enabled else ""
    bin_target = f"$(BUILD_DIR)/{artifact}.bin" if flash_enabled and flash_format in {"binary", "bin"} else ""
    list_target = f"$(BUILD_DIR)/{artifact}.lst" if list_enabled else ""
    generated_targets = [f"$(ELF)"]
    if hex_target:
        generated_targets.append(hex_target if not bin_target else bin_target)
    if list_target:
        generated_targets.append(list_target)

    lines: list[str] = [
        "# Auto-generated by tools/wvproj_to_make.py.  Do not edit the EVT source tree.",
        f"# Input: {config['wvproj']}",
        f"# Project metadata: {config.get('format')}",
        "SHELL := /bin/sh",
        "MAKEFLAGS += --no-builtin-rules --no-builtin-variables",
        "RM := rm -f",
        "",
        f"PROJECT_DIR := {make_escape(config['project_dir'])}",
        "MAKEFILE_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))",
        "BUILD_DIR ?= $(abspath $(MAKEFILE_DIR)obj)",
        f"TOOLCHAIN_ROOT ?= {make_escape(str(toolchain['root']))}",
        f"TOOLCHAIN_BIN ?= {make_escape(str(toolchain['bin']))}",
        f"CROSS_PREFIX ?= {toolchain['prefix']}",
        f"COMPILER_PATH ?= {make_escape(str(toolchain['compiler']))}",
        "CC := $(COMPILER_PATH)",
        "CXX := $(TOOLCHAIN_BIN)/$(CROSS_PREFIX)g++",
        "AS := $(TOOLCHAIN_BIN)/$(CROSS_PREFIX)as",
        "OBJCOPY := $(TOOLCHAIN_BIN)/$(CROSS_PREFIX)objcopy",
        "OBJDUMP := $(TOOLCHAIN_BIN)/$(CROSS_PREFIX)objdump",
        "SIZE := $(TOOLCHAIN_BIN)/$(CROSS_PREFIX)size",
        "",
        f"TARGET_FLAGS := {make_words(flags['target'])}",
        f"CPPFLAGS := {make_words(cppflags)}",
        f"CFLAGS := {make_words(flags['cflags'])}",
        f"ASFLAGS := {make_words(asflags)}",
        f"LDFLAGS := {make_words(ldflags)}",
        f"LDLIBS := {make_words(other_objects)}",
        f"SOURCES := {' '.join(make_escape(str(source)) for source in sources)}",
        f"OBJECTS := {' '.join(make_escape(obj) for obj in objects)}",
        f"DEPS := {' '.join(make_escape(dep) for dep in depfiles)}",
        f"ELF := $(BUILD_DIR)/{artifact}.elf",
        "",
        f".PHONY: all clean size list flash print-config",
        f"all: {' '.join(generated_targets)} size",
        "",
        "$(BUILD_DIR):",
        "\t@mkdir -p $@",
        "",
        "$(ELF): $(OBJECTS) " + " ".join(make_escape(str(path)) for path in scripts),
        "\t@mkdir -p $(@D)",
        "\t$(CC) $(TARGET_FLAGS) $(LDFLAGS) -o $@ $(OBJECTS) $(LDLIBS)",
        "",
    ]

    if hex_target:
        if bin_target:
            lines.extend([
                f"{bin_target}: $(ELF)",
                "\t@mkdir -p $(@D)",
                "\t$(OBJCOPY) -O binary $< $@",
                "",
            ])
        else:
            lines.extend([
                f"{hex_target}: $(ELF)",
                "\t@mkdir -p $(@D)",
                "\t$(OBJCOPY) -O ihex $< $@",
                "",
            ])
    if list_target:
        lines.extend([
            f"{list_target}: $(ELF)",
            "\t@mkdir -p $(@D)",
            "\t$(OBJDUMP) -h -S $< > $@",
            "",
        ])

    for source, obj in source_objects:
        source_text = make_escape(str(source))
        if source.suffix in {".S", ".s", ".sx"}:
            compiler = "$(CC)"
            recipe_flags = "$(TARGET_FLAGS) $(CPPFLAGS) $(ASFLAGS)"
        elif source.suffix.lower() in {".cc", ".cpp", ".cxx"}:
            compiler = "$(CXX)"
            recipe_flags = "$(TARGET_FLAGS) $(CPPFLAGS) $(CFLAGS)"
        else:
            compiler = "$(CC)"
            recipe_flags = "$(TARGET_FLAGS) $(CPPFLAGS) $(CFLAGS)"
        lines.extend([
            f"{make_escape(obj)}: {source_text}",
            "\t@mkdir -p $(@D)",
            f"\t{compiler} {recipe_flags} -MMD -MP -c \"$<\" -o $@",
            "",
        ])

    lines.extend([
        "size: $(ELF)",
        "\t$(SIZE) $<",
        "",
        "list: " + (list_target or "$(ELF)"),
        "",
        "flash: " + (hex_target or "$(ELF)"),
        "",
        "print-config:",
        "\t@printf '%s\\n' '$(CC)' 'TARGET_FLAGS=$(TARGET_FLAGS)' 'CPPFLAGS=$(CPPFLAGS)' 'CFLAGS=$(CFLAGS)' 'ASFLAGS=$(ASFLAGS)' 'LDFLAGS=$(LDFLAGS)'",
        "",
        "clean:",
        "\t$(RM) -r $(BUILD_DIR)",
        "",
        "-include $(DEPS)",
        "",
    ])
    (output_dir / "Makefile").write_text("\n".join(lines), encoding="utf-8")

    manifest = dict(config)
    manifest["output_dir"] = str(output_dir)
    manifest["toolchain"] = toolchain
    manifest["sources"] = [str(source) for source in sources]
    manifest["source_warnings"] = source_warnings
    manifest["resolved_flags"] = {
        "target": flags["target"],
        "cppflags": cppflags,
        "cflags": flags["cflags"],
        "asflags": asflags,
        "ldflags": ldflags,
        "other_objects": other_objects,
        "linker_scripts": [str(path) for path in scripts],
    }
    (output_dir / "config.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wvproj", type=Path, help="input .wvproj file")
    parser.add_argument("-o", "--output", type=Path, required=True, help="directory for generated Makefile and config.json")
    parser.add_argument("--gcc-root", type=Path, help="root containing darwin-arm64/ and linux-amd64/ (default: ../gcc)")
    parser.add_argument("--platform", choices=["darwin-arm64", "linux-amd64"], help="override host platform selection")
    parser.add_argument(
        "--compiler-path",
        "--compiler",
        dest="compiler_path",
        type=Path,
        help="explicit GCC executable; takes precedence over --platform and automatic host selection",
    )
    parser.add_argument(
        "--gcc-major",
        type=int,
        help="override the GCC major version requested by MRS metadata; an explicit value is "
        "always honoured and selects the matching -march dialect",
    )
    parser.add_argument("--quiet", action="store_true", help="only report errors")
    args = parser.parse_args(argv)

    try:
        config = load_project(args.wvproj)
        sources, source_warnings = collect_sources(config)
        if args.compiler_path is not None:
            toolchain = select_explicit_compiler(config, args.compiler_path)
        else:
            host_platform = args.platform or detect_platform()
            gcc_root = (args.gcc_root or Path(__file__).resolve().parents[2] / "gcc").resolve()
            requested_major = args.gcc_major if args.gcc_major is not None else normalized_toolchain_major(config)
            toolchain = select_toolchain(
                config, gcc_root, host_platform, requested_major, explicit_major=args.gcc_major is not None
            )
        manifest = build_makefile(config, args.output, toolchain, sources, source_warnings)
    except (OSError, ET.ParseError, ValueError, KeyError) as exc:
        print(f"wvproj_to_make.py: error: {exc}", file=sys.stderr)
        return 2

    if not args.quiet:
        print(f"generated {Path(manifest['output_dir']) / 'Makefile'}")
        print(f"  input format: {manifest['format']}")
        if manifest.get("encrypted_wvproj"):
            print(f"  encrypted .wvproj fallback: {manifest['companion_cproject']}")
        print(f"  sources: {len(manifest['sources'])}")
        print(f"  toolchain: {manifest['toolchain']['platform']} {manifest['toolchain']['version']} ({manifest['toolchain']['prefix']})")
        if manifest['toolchain'].get("explicit_compiler"):
            print(f"  explicit compiler: {manifest['toolchain']['compiler']}")
        if manifest['toolchain'].get("version_probe_warning"):
            print(f"  warning: {manifest['toolchain']['version_probe_warning']}")
        if manifest['toolchain'].get("compatibility_upgrade"):
            print(
                f"  warning: GCC {manifest['toolchain']['requested_major']} does not support the "
                f"project ISA flags; selected GCC {manifest['toolchain']['version']}"
            )
        elif manifest['toolchain'].get("fallback"):
            print(f"  warning: requested GCC {manifest['toolchain']['requested_major']} was unavailable; selected {manifest['toolchain']['version']}")
        for warning in manifest.get("source_warnings", []):
            print(f"  warning: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
