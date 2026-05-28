# XHS-Downloader 项目结构说明

## 项目概览

本项目基于 [JoeanAmier/XHS-Downloader](https://github.com/JoeanAmier/XHS-Downloader)，是一个小红书（Xiaohongshu）内容下载工具。原作者提供了完整的下载引擎，我在其基础上添加了自己的脚本以满足批量下载需求。

## 文件归属

### 原作者文件
| 文件 | 说明 |
|:----|:----|
| `main.py` | 官方入口，支持交互模式 / API / MCP / CLI |
| `source/` | 核心源码包（下载引擎、设置、UI、API） |
| `pyproject.toml` | 项目配置和依赖 |
| `README.md` / `README_EN.md` | 官方文档 |
| `example.py` | 官方示例 |

### 我的脚本
| 文件 | 说明 |
|:----|:----|
| `dl.py` | 批量下载器。从 `1.txt` 读取链接，预过滤已下载的，逐个下载（带随机间隔） |
| `1.txt` | 手动维护的链接队列，油猴脚本收集后粘贴于此 |
| `failed.txt` | 自动生成，记录下载失败的链接，供下次重试 |

## 我的脚本与原作者的关系

```
dl.py（我的调度器）
  │
  ├── Settings(ROOT).run()  ← 原作者配置读取
  ├── XHS(**params)         ← 原作者类实例化
  └── xhs.extract_cli()     ← 原作者下载接口（cookie、UA、代理、断点续传全部走原作者）
```

`dl.py` 是一个**胶水层**，不修改原作者任何代码。
- 下载能力全部来自原作者
- 调度逻辑（间隔、重试、过滤）是我自己写的

## 关键路径

### 数据文件
```
项目根目录/
├── 1.txt                 # 输入：油猴脚本收集的链接（空格分隔）
├── failed.txt            # 输出：下载失败的链接
├── dl.py                 # 我的批量下载器
└── Volume/
    ├── ExploreID.db      # 下载记录库（原作者自动维护）
    ├── ExploreData.db    # 作品数据库（可选，record_data=True时）
    └── settings.json     # 配置文件（cookie、UA、代理等）
```

### 过滤已下载链接的逻辑（在 dl.py 中）
```
1.txt 链接
  ↓
extract_id_from_url()  →  提取 /item/xxxxxxxx?... 中的 ID
  ↓
read_downloaded_ids()  →  查询 Volume/ExploreID.db 的 explore_id 表
  ↓
比对 → 只处理未下载的链接（零网络请求跳过已下载的）
```

`dl.py` 仅在**预过滤阶段**直接读 SQLite（用 Python 内置 sqlite3），实际下载全程走原作者 API，自动写入下载记录。

## 运行方式

```bash
python dl.py          # 批量下载（我写的）
python main.py        # 原作者主程序（交互/API/MCP/CLI）
```

## 注意事项

- `dl.py` 的间隔默认 30-60 秒随机，防止被封
- 如果数据库不存在（首次运行），`dl.py` 会处理所有链接，不会报错
- 失败链接写入 `failed.txt`，可修复后重新跑
- 若原作者更新代码，`dl.py` 无需修改即可适配（只要 `XHS()` 和 `extract_cli()` 接口不变）
