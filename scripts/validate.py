#!/usr/bin/env python3
"""校验本仓库使用的 Shadowrocket 配置语法、引用和规则顺序；仅依赖标准库。"""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import ipaddress
import logging
from pathlib import Path
import re
import shlex
from urllib.parse import urlsplit
from urllib.request import urlopen


BUILTIN_POLICIES = {"DIRECT", "PROXY", "REJECT"}
LIST_TYPES = {"DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "USER-AGENT", "URL-REGEX", "IP-CIDR", "IP-CIDR6"}


def split_fields(text: str) -> list[str]:
    """只在括号外拆分逗号，保留 AND / OR 中嵌套的匹配条件。"""
    fields, depth, start = [], 0, 0
    for index, char in enumerate(text):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                raise ValueError("条件括号不匹配")
        elif char == "," and depth == 0:
            fields.append(text[start:index].strip())
            start = index + 1
    if depth:
        raise ValueError("条件括号不匹配")
    fields.append(text[start:].strip())
    if not all(fields):
        raise ValueError("规则包含空字段")
    return fields


def check_url(value: str) -> None:
    """限制远程资源为带有效主机名的 HTTPS 地址。"""
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or re.search(r"\s", value):
        raise ValueError("远程资源必须使用有效的 HTTPS 地址")


def check_matcher(kind: str, value: str) -> None:
    """检查当前项目用到的匹配条件，不模拟客户端的网络和 GeoIP 行为。"""
    if kind in {"DOMAIN", "DOMAIN-SUFFIX"}:
        labels = value.split(".")
        if len(value) > 253 or not all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels):
            raise ValueError("域名格式无效，应使用不带通配符的小写域名")
    elif kind in {"IP-CIDR", "IP-CIDR6"}:
        network = ipaddress.ip_network(value, strict=True)
        # 上游 Shadowrocket 列表使用 IP-CIDR 表示两种地址族，保留此兼容格式。
        if kind == "IP-CIDR6" and network.version != 6:
            raise ValueError("IP-CIDR6 必须使用 IPv6 网段")
    elif kind == "URL-REGEX":
        re.compile(value)
    elif kind == "GEOIP":
        if not re.fullmatch(r"[A-Z]{2}", value):
            raise ValueError("GEOIP 必须使用两位大写地区代码")
    elif kind == "PROTOCOL":
        if value not in {"TCP", "UDP"}:
            raise ValueError("PROTOCOL 仅支持 TCP / UDP")
    elif kind == "DST-PORT":
        if not value.isdigit() or not 1 <= int(value) <= 65535:
            raise ValueError("目标端口必须介于 1 与 65535 之间")
    elif kind in {"AND", "OR", "NOT"}:
        if not (value.startswith("(") and value.endswith(")")):
            raise ValueError("逻辑条件缺少外层括号")
        conditions = split_fields(value[1:-1])
        if (kind == "NOT" and len(conditions) != 1) or (kind != "NOT" and len(conditions) < 2):
            raise ValueError("逻辑条件数量不正确")
        for condition in conditions:
            if not (condition.startswith("(") and condition.endswith(")")):
                raise ValueError("子条件缺少括号")
            fields = split_fields(condition[1:-1])
            if len(fields) != 2:
                raise ValueError("子条件必须包含类型和值")
            check_matcher(*fields)
    elif kind not in {"DOMAIN-KEYWORD", "USER-AGENT"}:
        raise ValueError(f"校验器尚未支持此规则类型：{kind}")
    if not value.strip():
        raise ValueError("匹配值不能为空")


class Validator:
    """收集文件位置明确的错误，并保存可供网络检查使用的外部规则链接。"""

    def __init__(self, root: Path) -> None:
        """绑定待检查的仓库目录，避免依赖命令调用时的工作目录。"""
        self.root = root
        self.errors: list[str] = []
        self.remote_urls: set[str] = set()

    def error(self, location: str, message: str) -> None:
        """统一记录错误，允许一次检查报告多个问题。"""
        self.errors.append(f"{location}: {message}")

    def read(self, path: Path) -> list[tuple[int, str]]:
        """读取非空、非注释行，同时检查 UTF-8、末尾换行和行末空白。"""
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            self.error(path.name, str(error))
            return []
        if not content.endswith("\n"):
            self.error(path.name, "文件末尾缺少换行")
        rows = []
        for number, line in enumerate(content.splitlines(), 1):
            if line != line.rstrip():
                self.error(f"{path.name}:{number}", "存在行末空白")
            if line.strip() and not line.lstrip().startswith("#"):
                rows.append((number, line.strip()))
        return rows

    def check_list(self, path: Path) -> int:
        """检查无策略的规则列表、重复规则和现有头部统计。"""
        rows = self.read(path)
        counts: Counter[str] = Counter()
        seen = set()
        for number, line in rows:
            try:
                fields = [field.strip() for field in line.split(",")]
                kind, value = fields[:2]
                if kind not in LIST_TYPES:
                    raise ValueError(f"不支持的列表规则类型：{kind}")
                expected = 3 if kind in {"IP-CIDR", "IP-CIDR6"} else 2
                if len(fields) != expected or (expected == 3 and fields[2] != "no-resolve"):
                    raise ValueError("列表不应包含策略；IP 规则需附带 no-resolve")
                check_matcher(kind, value)
                normalized = tuple(fields)
                if normalized in seen:
                    raise ValueError("存在重复规则")
                seen.add(normalized)
                counts[kind] += 1
            except (ValueError, re.error) as error:
                self.error(f"{path.name}:{number}", str(error))
        if not rows:
            self.error(path.name, "规则列表不能为空")
        try:
            metadata = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return 0
        for kind, amount in re.findall(r"^# ([A-Z-]+): (\d+)\s*$", metadata, re.MULTILINE):
            if kind in LIST_TYPES | {"TOTAL"}:
                actual = len(rows) if kind == "TOTAL" else counts[kind]
                if int(amount) != actual:
                    self.error(path.name, f"{kind} 统计为 {amount}，实际为 {actual}")
        return len(rows)

    def assignments(self, rows: list[tuple[int, str]], section: str) -> dict[str, str]:
        """读取键值配置并拒绝重复键，防止隐式覆盖配置项或策略组。"""
        values = {}
        for number, line in rows:
            key, separator, value = line.partition("=")
            key, value = key.strip(), value.strip()
            if not separator or not key or not value or key in values:
                self.error(f"Shadowrocket.conf:{number}", f"[{section}] 键值格式错误或键重复：{key}")
            else:
                values[key] = value
        return values

    def check_config(self, list_names: set[str]) -> None:
        """验证分区、策略组依赖、远程列表引用及易被通用规则遮蔽的优先级。"""
        sections: dict[str, list[tuple[int, str]]] = {}
        current = ""
        for number, line in self.read(self.root / "Shadowrocket.conf"):
            if line.startswith("[") and line.endswith("]"):
                current = line[1:-1]
                if current in sections:
                    self.error(f"Shadowrocket.conf:{number}", f"分区重复：{current}")
                sections.setdefault(current, [])
            elif not current:
                self.error(f"Shadowrocket.conf:{number}", "配置项必须位于分区内")
            else:
                sections[current].append((number, line))
        for name in ("General", "Proxy Group", "Rule", "Host"):
            if not sections.get(name):
                self.error("Shadowrocket.conf", f"缺少非空 [{name}] 分区")
        general = self.assignments(sections.get("General", []), "General")
        self.assignments(sections.get("Host", []), "Host")
        update_url = general.get("update-url", "")
        try:
            check_url(update_url)
            if not update_url.endswith("/Shadowrocket.conf"):
                raise ValueError("update-url 必须指向 Shadowrocket.conf")
        except ValueError as error:
            self.error("[General] update-url", str(error))
        local_prefix = update_url.rsplit("/", 1)[0] + "/"
        groups = self.assignments(sections.get("Proxy Group", []), "Proxy Group")
        policies = BUILTIN_POLICIES | groups.keys()
        dependencies = {}
        for name, definition in groups.items():
            try:
                fields = [field.strip() for field in definition.split(",")]
                mode, members, options = fields[0], [], {}
                if mode not in {"select", "url-test"}:
                    raise ValueError(f"不支持的策略组类型：{mode}")
                for field in fields[1:]:
                    key, separator, value = field.partition("=")
                    if separator:
                        if key in options or not value:
                            raise ValueError(f"策略组选项重复或为空：{key}")
                        options[key] = value
                    else:
                        members.append(field)
                if name in BUILTIN_POLICIES:
                    raise ValueError("策略组不能覆盖内置策略")
                if any(member not in policies for member in members):
                    raise ValueError("策略组引用了未定义的策略")
                if mode == "select" and not members:
                    raise ValueError("select 策略组不能为空")
                if mode == "select" and options.get("policy-select-name", members[0]) not in members:
                    raise ValueError("默认策略必须属于该策略组")
                if "policy-regex-filter" in options:
                    re.compile(options["policy-regex-filter"])
                dependencies[name] = [member for member in members if member in groups]
            except (ValueError, re.error) as error:
                self.error(f"[Proxy Group] {name}", str(error))

        def visit(name: str, chain: tuple[str, ...]) -> None:
            """检测组依赖循环，避免策略组间相互引用。"""
            if name in chain:
                self.error("[Proxy Group]", "策略组循环引用：" + " -> ".join((*chain, name)))
                return
            for child in dependencies.get(name, []):
                visit(child, (*chain, name))

        for name in groups:
            visit(name, ())
        seen, referenced, positions = set(), set(), {}
        rules = sections.get("Rule", [])
        final_count = 0
        for index, (number, line) in enumerate(rules):
            try:
                fields = split_fields(line)
                kind = fields[0]
                if kind == "FINAL":
                    final_count += 1
                    if len(fields) != 2 or index != len(rules) - 1:
                        raise ValueError("FINAL 必须是最后一条规则，且只包含策略")
                    policy = fields[1]
                else:
                    if len(fields) not in {3, 4}:
                        raise ValueError("主配置规则必须包含类型、匹配值、策略和可选的 no-resolve")
                    kind, value, policy = fields[:3]
                    if len(fields) == 4 and (kind not in {"IP-CIDR", "IP-CIDR6", "GEOIP"} or fields[3] != "no-resolve"):
                        raise ValueError("无效的规则附加参数")
                    if kind in {"RULE-SET", "DOMAIN-SET"}:
                        check_url(value)
                        filename = urlsplit(value).path.rsplit("/", 1)[-1]
                        positions[filename] = index
                        if value.startswith(local_prefix):
                            if filename not in list_names or value != local_prefix + filename or kind != "RULE-SET":
                                raise ValueError("本仓库规则列表引用不存在或格式错误")
                            referenced.add(filename)
                        else:
                            if filename in list_names:
                                raise ValueError("本地列表引用与 update-url 所在仓库或分支不一致")
                            self.remote_urls.add(value)
                    else:
                        check_matcher(kind, value)
                if policy not in policies:
                    raise ValueError(f"未定义的策略：{policy}")
                normalized = tuple(fields)
                if normalized in seen:
                    raise ValueError("存在重复规则")
                seen.add(normalized)
            except (ValueError, re.error) as error:
                self.error(f"Shadowrocket.conf:{number}", str(error))
        if final_count != 1:
            self.error("[Rule]", "必须且只能存在一条 FINAL")
        for filename in sorted(list_names - referenced):
            self.error("[Rule]", f"本地列表未被引用：{filename}")
        # 专用服务与宽泛服务之间存在交集，单纯通过语法检查无法发现顺序回归。
        for first, later in [("YouTube.list", "Google.list"), ("Mail.list", "Google.list"),
                             ("Mail.list", "Apple.list"), ("AI.list", "Apple.list"),
                             ("AI.list", "Microsoft.list"), ("ApplePush.list", "Apple.list")]:
            if first in positions and later in positions and positions[first] >= positions[later]:
                self.error("[Rule]", f"{first} 必须位于 {later} 之前")
        if positions.get("Amazon.list") != 0 or not rules[0][1].endswith(",DIRECT"):
            self.error("[Rule]", "Amazon.list 必须作为第一条规则并使用 DIRECT")
        for number, line in sections.get("URL Rewrite", []):
            try:
                pattern, target, status = shlex.split(line)
                re.compile(pattern)
                check_url(target)
                if status not in {"301", "302", "307", "308"}:
                    raise ValueError("不支持的重定向状态码")
            except (ValueError, re.error) as error:
                self.error(f"Shadowrocket.conf:{number}", str(error))

    def check_remote(self) -> None:
        """可选检查第三方列表可下载且包含规则；本仓库引用始终以本地文件为准。"""
        def fetch(url: str) -> tuple[str, str]:
            """为单个资源设置超时，将网络异常转换为带链接的诊断。"""
            try:
                with urlopen(url, timeout=20) as response:
                    content = response.read().decode("utf-8-sig")
                entries = [line.strip() for line in content.splitlines() if line.strip() and not line.lstrip().startswith("#")]
                if not entries or any(line.startswith("<") for line in entries):
                    raise ValueError("响应为空或返回了 HTML，未获取到规则")
                return url, ""
            except (OSError, ValueError, UnicodeError) as error:
                return url, str(error)

        with ThreadPoolExecutor(max_workers=6) as pool:
            for url, error in pool.map(fetch, sorted(self.remote_urls)):
                if error:
                    self.error(url, error)
                else:
                    logging.info("远程资源可用：%s", url)


def main() -> int:
    """执行离线校验，按需检查外部资源；失败时返回非零退出码供 CI 使用。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1], help="待检查的仓库目录")
    parser.add_argument("--check-remote", action="store_true", help="额外联网检查第三方规则集")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    validator = Validator(args.root)
    lists = sorted(args.root.glob("*.list"))
    count = sum(validator.check_list(path) for path in lists)
    validator.check_config({path.name for path in lists})
    if args.check_remote and not validator.errors:
        validator.check_remote()
    for error in validator.errors:
        logging.error("%s", error)
    if validator.errors:
        logging.error("校验失败，共 %d 个问题", len(validator.errors))
        return 1
    logging.info("校验通过：%d 个本地列表、%d 条列表规则、主配置及策略引用均有效", len(lists), count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
