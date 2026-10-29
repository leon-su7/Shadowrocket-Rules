# Shadowrocket 分流规则

[![配置校验](https://github.com/leon-su7/Shadowrocket-Rules/actions/workflows/validate.yml/badge.svg)](https://github.com/leon-su7/Shadowrocket-Rules/actions/workflows/validate.yml)

个人维护的 Shadowrocket 配置，覆盖 Amazon、Figma、AI、Google、Apple、邮件、香港银行与券商等服务。基于 [LingJingMaster/Shadowrocket-Rules](https://github.com/LingJingMaster/Shadowrocket-Rules) 整理，当前配置及自维护规则均从本仓库更新。

本项目提供分流规则，不包含代理节点或订阅。

## 快速开始

1. 复制当前仓库的配置链接：

   ```text
   https://raw.githubusercontent.com/leon-su7/Shadowrocket-Rules/refs/heads/main/Shadowrocket.conf
   ```

2. 打开 Shadowrocket，进入「配置」，通过右上角的 `+` 添加链接并下载，然后将该配置设为使用中。
3. 在首页添加自己的节点或订阅，将「全局路由」设为「配置」。
4. 检查「节点选择」及各服务策略，确认对应地区组中存在可用节点后连接。

地区组按节点名称筛选香港、台湾、日本、美国和其他地区节点。AI 默认使用台湾组，券商默认使用香港组；订阅没有对应节点时，请手动切换到可用策略。地区组使用 `url-test` 自动测速；美国组保留当前配置中的选中节点 `【CHATGPT】美国原生-03`，订阅更新后请检查该节点是否仍存在。

后续更新需同时刷新远程配置和规则集。配置的 `update-url` 已指向本仓库；如果从其他项目导入，请使用上面的链接重新下载。更新远程配置前，建议备份自己修改过的配置及策略选择。

## 默认分流

下表描述配置中的初始选择。客户端中已经保存的手动选择可能与此不同。

| 服务 | 默认策略 | 说明 |
| --- | --- | --- |
| 节点选择 | `PROXY` | 使用客户端当前选择的代理节点 |
| Amazon | `DIRECT` | 固定直连，优先级最高 |
| Figma | `PROXY` | 固定代理，覆盖 Design、FigJam、Slides、Buzz、Make、Sites、Weave 及资源上传下载 |
| DNS 防泄露 | `REJECT` | 拦截所引用规则集收录的 HTTPDNS 地址 |
| AI 服务 | 台湾节点 | ChatGPT、Claude、Apple Intelligence、Copilot、Grok 等；可切换美国等策略 |
| 谷歌服务 | 节点选择 | 包含 Gemini、AI Studio、NotebookLM |
| 油管视频 | 节点选择 | YouTube 及配置中指定的翻译接口 |
| 微软服务 | `DIRECT` | 可手动切换到节点选择 |
| 邮件服务 | `DIRECT` | 仅邮件协议端点，网页邮箱仍按所属服务分流 |
| 苹果服务、苹果推送 | `DIRECT` | AI 专用端点与邮件端点优先使用各自策略 |
| 电报消息、代码托管 | 节点选择 | 代码托管包含 GitHub、GitLab、Atlassian |
| 汇丰香港、其他香港银行 | `DIRECT` | 两组均可手动切换到香港节点 |
| 券商服务 | 香港节点 | 覆盖富途、Moomoo、长桥、老虎、雪盈、盈透、Schwab 等 |
| 私有网络、国内服务 | `DIRECT` | 包含国内 IP 与哔哩哔哩等专用规则 |
| 非中国 | 节点选择 | 命中 Global 规则集的流量，跟随「节点选择」统一切换 |
| 漏网之鱼 | `DIRECT` | 所有规则均未命中后的最终兜底 |

## 规则顺序

`[Rule]` 按顺序匹配，专用规则应放在宽泛规则之前：

1. Amazon 固定直连。
2. Figma 及其网络依赖固定代理。
3. 自定义域名、微信、局域网域名、国内 AI，以及保留的端口和 IP 特例。
4. HTTPDNS、邮件、YouTube 翻译接口与 YouTube 规则。
5. Google、AI，以及哔哩哔哩、局域网、Telegram、代码托管、Microsoft 等服务。
6. 香港银行、券商、苹果推送与 Apple 规则。
7. China、Global、`GEOIP,CN` 和最后的 `FINAL`。

YouTube 必须位于 Google 之前，避免 `googlevideo.com` 等流量被 Google 的域名关键字规则提前匹配。邮件需位于 Google 和 Apple 之前；AI 需位于 Microsoft 和 Apple 之前；苹果推送需位于 Apple 之前。

## 文件说明

| 文件 | 内容 |
| --- | --- |
| [Shadowrocket.conf](Shadowrocket.conf) | 主配置、DNS、策略组和分流顺序 |
| [Amazon.list](Amazon.list) | Amazon 各地区商城、账号、支付、卖家后台、商品短链接、静态资源与 Prime Video |
| [Figma.list](Figma.list) | Figma 官方网络清单、自有域名、快捷入口、验证码、Make 依赖及专用资源桶 |
| [AI.list](AI.list) | Apple Intelligence、ChatGPT、Claude、Copilot、Grok、OpenRouter、Perplexity |
| [Google.list](Google.list) | Google 通用服务及 Gemini、AI Studio、NotebookLM 等 |
| [Apple.list](Apple.list) | Apple、iCloud、CloudKit、CDN 与相关地址段 |
| [ApplePush.list](ApplePush.list) | Apple 推送域名；一条后缀规则覆盖其子域名 |
| [Mail.list](Mail.list) | Apple、Gmail、Outlook、Yahoo、Yandex 的 IMAP、POP3、SMTP 端点 |
| [HSBC_HK.list](HSBC_HK.list) | 汇丰香港及相关应用端点 |
| [HK_Banks_Direct.list](HK_Banks_Direct.list) | 其他香港银行及虚拟银行 |
| [HK_Broker.list](HK_Broker.list) | 香港与美国券商域名、交易和行情 IP |
| [scripts/validate.py](scripts/validate.py) | 仅使用 Python 标准库的配置校验工具 |
| [.github/workflows/validate.yml](.github/workflows/validate.yml) | 推送、拉取请求及手动触发的离线检查 |

本地 `.list` 文件不包含策略，策略由主配置中的 `RULE-SET` 引用指定。现有部分头部统计会由校验器核对，完整数量以校验输出为准。

## DNS 与特殊规则

- 默认 DNS 使用经过代理访问的 Cloudflare DoH，备用为 Google DoH；国内直连解析和局域网解析保留系统 DNS 路径。组名「DNS 防泄露」仅表示 HTTPDNS 拦截用途，不代表消除全部 DNS 泄露。
- 默认关闭 IPv6 和代理流量的 QUIC；这些设置可在 `[General]` 中按需调整。
- `skip-proxy`、`tun-excluded-routes` 和 `[Host]` 也会影响请求处理，排查时应与 `[Rule]` 一起查看。
- 保留 TCP 目标端口 `5223` 使用「苹果推送」策略的规则，该规则会影响所有使用此端口的 TCP 连接。
- 保留 `208.54.0.0/16` 使用美国节点的 IP 特例，以及 `haowallpaper.com` 固定直连规则。
- Google 中国域名重写只匹配 `g.cn`、`google.cn` 及其 `www` 主机。配置不附带 MITM 证书，HTTPS 重写需要在客户端另行配置。银行列表中按 HTTPS 路径匹配的 `URL-REGEX` 同样依赖客户端能够读取相应 URL。

Amazon 的 `amazonaws.com` 和 `cloudfront.net` 属于共享云服务域名，未整体加入直连列表，避免影响第三方服务。Amazon 站点、支付和视频的直连策略不改变服务自身的地区限制。

Figma 清单于 2026-10-29 核对官方网络要求和公开客户端配置，涵盖截图中的全部域名，并补充 API 导出、字体、剪贴板、社区图片、Make 代码导入等资源。主域名使用后缀规则覆盖全部子域名；专用 S3 桶使用包含 `.s3` 的桶名关键字覆盖不同区域、加速和双栈端点。它不会将整个 AWS 或 CloudFront 设为代理。

Figma 官方要求中的 `arkoselabs.com`、`awswaf.com`、`esm.sh`、`jsdelivr.net` 和 `prodregistryv2.org` 也是共享服务，因此这些域名的其他流量同样会走代理。域名清单会随产品更新；第三方插件、自定义网站和外部集成使用的任意域名需另行添加。

## 维护与校验

使用 Python 3.9 或更新版本，在仓库目录运行：

```sh
python3 scripts/validate.py
```

离线检查覆盖列表语法、域名和 CIDR、重复规则、现有头部统计、配置分区、策略引用与循环依赖、本地列表引用、关键规则顺序、`FINAL` 和重写正则。失败会输出文件位置及错误，并返回非零退出码。

额外检查第三方远程规则是否可下载：

```sh
python3 scripts/validate.py --check-remote
```

本仓库规则始终校验本地文件，网络选项仅检查第三方引用。GitHub Actions 执行离线检查，避免外部资源临时不可用导致提交检查失败。

新增规则时，请在对应列表中维护域名；不要给 `.list` 条目添加策略。新增列表还需在主配置中引用，并放在合适的优先级。修改已有统计头时同步更新数量；修改策略组名称时同步更新全部引用。

校验器覆盖本仓库当前采用的语法，并非完整的 Shadowrocket 配置解析器。它不验证节点连通性、服务可用地区或客户端实际匹配结果；修改后仍需在 Shadowrocket 中检查请求记录和命中策略。

## 来源与许可

- 原始配置：[LingJingMaster/Shadowrocket-Rules](https://github.com/LingJingMaster/Shadowrocket-Rules)。
- 主要第三方规则：[blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script)，主配置直接引用其中的 Shadowrocket 规则。
- Amazon 地区站点参考：[Amazon 全球销售](https://sell.amazon.com/global-selling)与[官方站点列表](https://affiliate-program.amazon.com/creatorsapi/docs/en-us/concepts/common-request-headers-and-parameters)。
- Figma 域名参考：[官方网络要求](https://help.figma.com/hc/en-us/articles/19424714305943-Adjust-your-network-settings)、[官方新建文件入口](https://help.figma.com/hc/en-us/articles/360038511153-Create-a-new-file)及 [Figma 公开应用配置](https://www.figma.com/login)；资源桶还核对了 AWS 返回的桶区域信息。
- Apple Intelligence 核心端点参考：[Apple 官方网络要求](https://support.apple.com/101555)。

本仓库使用 [MIT License](LICENSE)，保留原作者版权声明及规则文件中的来源标记。第三方规则的使用还应遵循其来源项目的许可说明。
