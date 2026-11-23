# BWIKI 皮肤（MediaWiki 1.46）

一套面向 MediaWiki 1.46 的自定义皮肤，视觉与交互对标 B 站游戏 Wiki（biligame）的 BWIKI 风格：
顶栏 logo 条 + 多级侧边菜单 + 内容页标题区（Wiki功能下拉 / 阅读信息 / 页面贡献者）+ 移动端全屏抽屉。

不依赖 `MediaWiki:Common.css`、`MediaWiki:Common.js`、原站 Widget 或任何外部 CDN 资源，皮肤自包含。

## 目录结构

```
mw-build/BWIKI/
├── skin.json                 # 皮肤注册（ValidSkinNames: bwiki）
├── includes/
│   ├── SkinBWIKI.php         # Mustache 皮肤主体：模板数据、Sidebar 树、标题区、用户状态、贡献者
│   └── HookHandler.php       # 静态资源挂载 + MediaWiki:BWIKI.css / BWIKI.js 注入
├── templates/
│   └── skin.mustache         # 页面骨架（顶栏 / 菜单 / 抽屉 / 内容容器）
├── resources/
│   ├── bundle/               # 官方打包的静态外观（bootstrap、rank、styles…）
│   ├── logo.svg
│   ├── skin.css              # 皮肤基础样式
│   ├── tune.css              # 对齐层：覆盖 bundle 的地方都在这（级联最后）
│   └── skin.js               # 交互层：下拉、抽屉、吸顶、多级折叠
└── i18n/{zh-hans,en}.json
```

## 关键实现

- **多级侧边栏**：MediaWiki 内核会把 `MediaWiki:Sidebar` 的 `***` 拍平成同级，因此皮肤自行解析 Sidebar 原文建树
  （`buildSidebarTree` / `renderDesktopTree` / `renderMobileTree`），桌面端下拉 + 移动端抽屉共用同一棵树。
- **移动抽屉**：`#bwikiDrawer` 全高面板，宽度 `min(84vw, 340px)`，`transform` 滑入；一级栏目点进去子菜单整屏右滑，
  更深层级用 `sub-open` 手风琴。遮罩 z-index 1090、抽屉 1100。
- **头像**：装有 SocialProfile 时用 `wAvatar` 输出头像图（顶栏与「页面贡献者」两处），否则回退首字母圆形徽标。
- **特殊页面**：`body.ns-special` 下隐藏「页面贡献者」「阅读/更新/最新编辑」「Wiki功能」等仅内容页才有意义的元素
  （部分元素带 Bootstrap 的 `visible-*-block`，需 `!important` 才能盖掉）。
- **字号**：编辑器与 Codex 表单（登录 / 参数设置）在 `tune.css` 恢复 14px —— 根因是 bootstrap 把 `html{font-size:10px}`，
  压扁了 MediaWiki 组件的 rem 单位。**不要动根字号**。

## 站点级定制挂载点

`HookHandler::onBeforePageDisplay` 只在 `skin=bwiki` 时追加两个页面挂载点：

| 页面 | 注入 | 位置 |
| --- | --- | --- |
| `MediaWiki:BWIKI.css` | `addInlineStyle` → 内联 `<style>` | 紧跟 `tune.css` 之后，同级特异性即可覆盖皮肤 |
| `MediaWiki:BWIKI.js` | `addInlineScript` | 延迟到 `mediawiki.util` + `jquery` 就绪后执行，可直接用 `$` 与 `mw.*` |

两个页面按纯文本读取（`TitleFactory` + `RevisionLookup`），空页 / 缺页不注入。

> 注意：内联脚本执行时 ResourceLoader 启动脚本可能还没定义 `mw`（会报 `mw is not defined`），
> 因此注入的包装代码用 `setTimeout` 轮询等待 `window.mw`，不要改回直接调用。

## 安装

1. 把 `BWIKI/` 放到 `$IP/skins/BWIKI/`。
2. `LocalSettings.php` 中：
   ```php
   wfLoadSkin( 'BWIKI' );
   $wgDefaultSkin = 'bwiki';
   ```
3. 可选：装 [SocialProfile](https://www.mediawiki.org/wiki/Extension:SocialProfile) 启用真实头像，并确保
   `images/avatars/` 可写（默认头像落在该目录）。

## 开发约定

- 改**静态样式**后必须递增 `includes/HookHandler.php` 的 `BUNDLE_VERSION`，否则浏览器命中旧缓存。
- 覆盖 `bundle/` 的规则统一写在 `resources/tune.css` 最后，靠加载顺序取胜；编辑器的 `bundle/` 文件不提交改动。
- 交互一律放 `resources/skin.js`，不要往模板里塞行内脚本。

## 工具脚本（`mw-build/`）

| 脚本 | 用途 |
| --- | --- |
| `ftp_push.py` | InfinityFree FTP 分块上传（STOR 16 字节种子 → APPE 1KB 分块 → 下载字节级校验），支持 `本地=远端` 多组与删除 |
| `cdp.py` | 零依赖 Chrome DevTools Protocol 客户端（纯 socket WebSocket），用于 headless 截图、触摸事件、DOM 断言 |
| `q_custom_pages.py` | 走 `api.php edit` 创建 / 更新 `MediaWiki:BWIKI.css|BWIKI.js` 并验证注入位置 |
| `manage_test_wiki.py` | 站点常规 API 操作（登录、建页等），凭据读环境变量 |
| `build_bundle.py` / `snap.py` | 构建静态资源包 / 页面快照 |

凭据统一放在 `mw-build/.secrets.env`（**已被 `.gitignore` 排除**）：

```
FTP_URL=ftp://user:pass@host/htdocs/
MW_HOST=https://your-wiki.example
MW_USER=...
MW_PASS=...
```

## 第三方资源说明

`resources/bundle/` 下是原站打包的样式与图片，版权归原站点所有，仅用于风格对齐的自托管部署；
若要公开分发本项目，请先确认该目录的处理方式（建议保持仓库私有，或替换为你自己的资源）。
