---
name: prototype-package
description: Package frontend product prototype projects for handoff and upload. Use when a product manager or Codex needs to turn a local frontend prototype built with Vue, React, Svelte, Angular, Vite, Vue CLI, Next.js static export, Nuxt static generation, or plain HTML/CSS/JavaScript into source_code.zip and dist.zip for cloud prototype deployment, project management upload,研发 review, or sharing outside the local machine. The skill identifies the frontend project, installs dependencies when needed, runs the build command when present, verifies static output, and produces standardized ZIP archives.
---

# Prototype Package

## 目标

把 Codex 生成的本地前端产品原型整理成两个标准交付物：

- `source_code.zip`：源码包，供研发查看、复现或二次开发。
- `dist.zip`：静态构建产物包，供项目管理系统上传并自动部署。

默认面向常见前端技术栈：Vue、React、Svelte、Angular、Vite、Vue CLI、Next.js 静态导出、Nuxt 静态生成，以及纯 HTML/CSS/JavaScript/TypeScript 原型。不要把部署平台逻辑写进原型项目；这个 skill 只负责本地打包与构建产物校验。

## 快速使用

优先运行随 skill 提供的脚本：

```bash
python3 ~/.codex/skills/prototype-package/scripts/package_prototype.py /path/to/prototype
```

脚本默认在项目根目录生成：

```text
source_code.zip
dist.zip
```

如果用户指定输出目录：

```bash
python3 ~/.codex/skills/prototype-package/scripts/package_prototype.py /path/to/prototype --output-dir /path/to/output
```

## 工作流

1. 定位原型项目根目录。优先使用用户给出的路径；否则从当前目录向下找最近的 `package.json` 或 `index.html`。如果工作区里有多个前端项目，先根据用户提到的项目名、最近修改时间或目录内容判断；不确定时只问一个问题。
2. 检查项目类型。Node 前端项目优先使用 `package.json` 里的 `scripts.build`；纯静态原型可直接使用已有 `index.html` 生成部署包。不要随意改业务代码来凑构建。
3. 运行脚本生成产物。脚本会：
   - 选择包管理器：`pnpm-lock.yaml`、`yarn.lock`、`package-lock.json`、`bun.lockb`、`bun.lock`，否则默认 `npm`。
   - 在 `node_modules` 不存在时自动安装依赖。
   - 在存在构建脚本时运行构建命令；纯静态项目则跳过构建。
   - 打包源码并递归排除 `node_modules`、构建目录、缓存、日志、历史 zip 和版本控制目录；排除规则对项目根目录及所有层级子目录同时生效。
   - 自动识别 `dist`、`build`、`out`、`.output/public`、Angular/Nuxt 常见嵌套输出，或按 `--dist-dir` 打包到 `dist.zip` 的根层级。
4. 验证输出。确认两个 zip 都存在且非空；确认 `dist.zip` 内含 `index.html`。如果没有 `index.html`，说明它可能不是可直接部署的静态站点，必须向用户说明风险。

## 产物约定

- `source_code.zip` 包含项目源码文件，路径从项目根开始，不包含外层项目目录。
- `source_code.zip` 在任意目录层级都必须排除 `.next`、`node_modules`、`out`、`dist`、`build`、缓存目录和历史 zip；只要路径中的任一目录段命中排除规则，就不要遍历或写入该目录。
- `dist.zip` 包含构建目录内部文件，路径从静态站点根开始；上传系统解压后应能直接看到 `index.html`。
- 默认自动识别构建目录，优先使用含 `index.html` 的 `dist`、`build`、`out`、`.output/public` 等目录。如项目使用其他输出目录，运行脚本时传 `--dist-dir build` 或对应目录名。
- 默认输出目录是项目根。用户要求集中收集产物时，用 `--output-dir` 指定。

## 处理常见问题

- 依赖安装失败：说明可能需要联网或私有 npm 源权限；按 Codex 的审批流程请求网络/命令权限，不要手写缺失依赖。
- 构建失败：先读错误日志，优先修复原型代码中明确的编译错误；不要绕过类型、lint 或构建错误生成假产物。纯静态项目没有构建命令时，可以用已有静态文件生成 `dist.zip`。
- 多项目仓库：不要把整个仓库当源码包。只打包用户要发布的原型项目目录。
- 已有旧 zip：脚本会覆盖同名 `source_code.zip` 和 `dist.zip`，但不会删除其他用户文件。
- 静态资源路径异常：优先检查 Vite `base`、Vue CLI `publicPath`、React `homepage`、Next.js `basePath`/`assetPrefix` 等配置。如果部署系统挂在域名根路径，通常应使用相对路径或 `/`；按项目实际情况调整并重新构建。

## 交付回复

完成后用简短中文回复用户：

```text
已生成：
- /abs/path/source_code.zip
- /abs/path/dist.zip

构建命令：npm run build
dist.zip 已校验包含 index.html。
```

如果构建或校验失败，回复必须包含失败命令、关键错误和已完成的产物状态。
