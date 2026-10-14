# 小火箭 Shadowrocket Config
### 原版请见：
   `https://raw.githubusercontent.com/LingJingMaster/Shadowrocket-Rules/refs/heads/main/Shadowrocket.conf`

## Amazon 直连规则

`Amazon.list` 包含 Amazon 各地区商城、账号登录、支付、卖家后台、商品分享短链接、图片资源和 Prime Video 域名。地区站点参考 [Amazon 官方全球销售页面](https://sell.amazon.com/global-selling) 和 [官方站点列表](https://affiliate-program.amazon.com/creatorsapi/docs/en-us/concepts/common-request-headers-and-parameters)。

主配置 `Shadowrocket.conf` 已在 `[Rule]` 开头引用该列表，并指定 `DIRECT`，优先于其他服务和通用规则集生效。共享的 `amazonaws.com`、`cloudfront.net` 域名保持原有分流。

新增列表及配置推送到 GitHub 的 `main` 分支后，更新 Shadowrocket 远程配置和规则集即可生效。

## License

MIT
