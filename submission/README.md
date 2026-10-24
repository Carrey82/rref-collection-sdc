# submission/ — 提交材料存放区

| 文件 | 内容 | 怎么来的 |
|---|---|---|
| `SDC2026_RREFCOLLECTION_Preliminary.pdf` | Phase 1 Project Proposal（官方模板七节） | `python3 submission/build_docs.py` |
| `SDC2026_RREFCOLLECTION_TechDeclaration.pdf` | Technical Tools Declaration（官方模板八节） | 同上 |
| `SDC2026_RREFCOLLECTION_PitchDeck.pptx` | 9 页 pitch deck | 设计工具导出 |
| `SDC2026_RREFCOLLECTION_Replit_POU.pdf` | Replit 使用证明（Handbook §10.6 的 (a)+(b)） | `python3 submission/pou/build_pou.py` |
| `build_docs.py` | 生成上面两份 PDF 的脚本，**正文都写在这里** | — |
| `pou/` | POU 截图与生成脚本 | — |
| **Demo video** | 6 分 48 秒英文演示，YouTube Unlisted：[https://youtu.be/351MYV8VjE8](https://youtu.be/351MYV8VjE8) | 录屏后剪掉停顿、标准化音量后上传 |

## 两份 PDF 的唯一正确改法

不要手动改 PDF。改 `build_docs.py` 里对应的常量，然后重新生成：

```bash
python3 submission/build_docs.py
```

脚本会做两件保护：

1. **字数超限直接报错**（官方八个字数上限都已写进 `check()` 调用），不会悄悄发出一份超字数的文档；
2. **顶部三个联系方式变量为空时提醒**（`MEMBERS` / `LEADER_EMAIL` / `LEADER_PHONE`），PDF 上会留一条空白线。

跑完在 `submission/` 下生成 `<名字>.pdf` 和一个同名 `.html`（html 已在 `.gitignore` 里）。Mac 上的 Chrome 路径写死在脚本顶部，换机器要改 `CHROME`；实在跑不通就用浏览器打开那个 `.html`，打印成 PDF，文件名照上面写。

## Replit 证明的取图原则

Handbook §10.6 只要三项里**任意一项**（live deployment URL / 带历史的 project link / credit 用尽），不需要截图。这个 PDF 是**辅助材料**，把已完成的证据归档：部署 URL 的真实响应头、仓库里提交的 `.replit`、提交时间线。
