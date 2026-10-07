# 论文图表模板

三种模板共用 [a175_mesh.csv](a175_mesh.csv)，数值逐项转录自 2023 A175 的 **PDF p.14 表3**。六个步长不是等间距，必须使用数值 X 轴。这里只复画表内结果，没有重新求解定日镜赛题；原文单位为 kW/m²，保留原表精度不表示精度已经得到验证。

## Matplotlib

需要 Python、Matplotlib。使用当前项目已确认的 Python 环境；在 CUMUM 工作区执行时遵守根 AGENTS.md 的解释器约定。下面的 `python` 代表该环境的解释器：

```powershell
python .\matplotlib_template.py
```

在模板目录运行；也可从其他目录传入脚本绝对路径。输出 [PNG 示例](mesh_sensitivity.png) 和可编辑文字的 [SVG 示例](mesh_sensitivity.svg)。脚本支持 `--data 文件.csv --output 输出目录`。替换 CSV 时保留列名，并在脚本中同步修改轴名、单位、来源和图题；这些标签不会自动推断。

## Origin

打开 [origin_template.ogs](origin_template.ogs)，把 `file$` 改为 CSV 的绝对路径，在 Origin Code Builder 中执行 `Main` 节。脚本导入两列并用 `plotxy` 的 202 类型生成 XY 连线加标记图、设置单位和来源。随后在 Plot Details 中设置单一蓝色、白底和浅灰 Y 网格，保存为自己的 `.otpu` 模板。没有附上未经生成的 `.otpu`。

命令依据 Origin 官方 [绘图说明](https://docs.originlab.com/labtalk/guide/creating-graphs/)、[ASCII 导入](https://docs.originlab.com/labtalk/examples/general-import/)和 [label 命令](https://docs.originlab.com/labtalk/ref/label-cmd/)。**已核对命令文档，当前机器没有 Origin，未验证实际执行与布局。**

## Excel

打开 [excel_template.xlsx](excel_template.xlsx)，在“数据”页修改 A/B 列数值。图表是原生 XY 散点连线图，无宏、公式或外部链接；增加数据行后需在“选择数据”中扩展范围。“说明”页保留来源和使用边界。可用安装了 openpyxl 的 Python 运行 `make_excel_template.py` 从 CSV 重建文件。

**已校验工作簿可重新读取、六行数据与 CSV 一致、图表指向 A2:A7/B2:B7；未在桌面 Excel 中检查渲染。**

## 套用与验收

1. 替换真实数据，同时改来源、轴名、单位、图题；不要保留 A175 标签冒充新结果。
2. 用表保留精确值，用图表达趋势；明确参考值与容差。最细网格值不等于真值。
3. 敏感性曲线要说明其余参数是否固定；随机算法的收敛图补充多次运行的分位带和运行次数。
4. 检查小字号、单位、来源、数值 X 轴及打印后可辨性，再导出论文图。

版本：2026-10-07。Matplotlib 已实际生成 PNG/SVG 并检查示例；Excel 校验范围与 Origin 未运行限制如上。
