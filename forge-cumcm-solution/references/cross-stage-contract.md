# 跨阶段最小事实契约

本文件只定义三个阶段必须共享的事实、版本和证据接口。具体建模、求解和写作方法分别由阶段 Skill 决定；不要为了满足清单制造无业务价值的表格。

## 1. 单一事实链

每项关键主张标记一种状态：

- `FACT`：题面、官方规则、原始数据或已核实外部事实；
- `ASSUMPTION`：为建模明确引入且尚非事实；
- `COMPUTED`：由已记录运行产生；
- `VERIFIED`：通过独立检查或可复算证据；
- `BLOCKED`：证据不足，不能继续引用为结论。

题面 → 对象/口径 → 模型 → 代码 → 输出 → 数字/图表 → 论文主张必须能双向追踪。阶段二不能私改阶段一事实；阶段三不能重算或手改阶段二数字。

## 2. 稳定 ID

对跨文件引用的对象使用简短稳定 ID，例如：

- 小问：`Q1`
- 模型：`M-Q1-BASE`
- 变量/约束：`VAR-*`、`CON-*`
- 运行：`RUN-*`
- 输出/数字/图：`OUT-*`、`NUM-*`、`FIG-*`
- 主张/证据：`CLAIM-*`、`EVID-*`

ID 一旦冻结不得换义。不同对象、场景、时间窗、分母或单位必须使用不同 ID；转换要登记来源、目标、公式和单位。

## 3. 本题执行合同

每阶段在专家评审前生成 `execution-record`。它与模型、代码、结果或论文一起纳入 `version-index`，至少包含：

```json
{
  "schema_version": "1.0",
  "stage": 1,
  "guide_snapshot_sha256": "综合指南哈希",
  "guide_sections": ["本阶段实际读取的章节"],
  "guide_applications": [
    {
      "guide_section": "指南章节",
      "current_task_action": "在当前题目实际执行的动作",
      "evidence_artifact_ids": ["产物 ID"]
    }
  ],
  "execution_contract": [
    {
      "question_id": "Q1",
      "task": "当前小问任务",
      "evidence_artifact_ids": ["产物 ID"],
      "acceptance": "本题化验收条件",
      "status": "COMPLETE"
    }
  ],
  "self_review": {
    "roles": [
      {
        "role_id": "本阶段角色",
        "criteria": [20, 20, 20, 20, 20],
        "findings": [],
        "evidence_artifact_ids": ["产物 ID"]
      }
    ]
  }
}
```

`guide_applications` 必须描述实际动作和证据，不能是“已阅读”“已遵循”或复制指南标题。执行合同覆盖全部官方小问和本阶段关键风险。机械脚本只核查这些记录存在且连接冻结产物；专业正确性由执行者和八席评审判断。

阶段一还必须保存 `proposal-input-packet`、`proposal-set` 和 `proposal-selection`。`proposal-set` 至少含八个不同 `proposer_id` 的候选，并登记动态新增方案 Agent 的专项理由；每个候选连接其搜索前独立思考、文献证据、融合模型、验证计划和文件哈希。`proposal-selection` 至少含八个阶段一角色，并登记动态新增评委的覆盖理由；所有选优评委必须对全部匿名候选给出逐项分数、证据、否决项、总分和排名，最后记录唯一胜者。匿名映射在全部评分封存前不得向评委公开。选优分数只决定主路线，不写入最终阶段评分，也不充当终审。

`execution-record` 还登记候选冻结时间和前五个已完成里程碑：
`LOAD_GUIDE`、`BUILD_EXECUTION_CONTRACT`、`HIGH_QUALITY_EXECUTION`、
`EXECUTOR_SELF_REVIEW`、`FREEZE_CANDIDATE`、
并随候选冻结。评审开始后另建不进入候选的 `stage-workflow-record`，只追加
`review_plan.required_role_ids`、`additional_role_ids` 和评审开始/完成时间。
它不得改写执行合同或自审证据。`INDEPENDENT_BLIND_REVIEW` 是评审记录中的第六个里程碑，不增加额外评审层。

## 4. 结果证据合同

阶段二逐问登记：

```json
{
  "question_id": "Q1",
  "answer_kind": "NUMERIC | CATEGORICAL | TEXT | PROOF | PLAN | FILE",
  "answer": "与类型相符的正式答案",
  "model_ids": ["M-*"],
  "code_locations": ["相对路径和定位"],
  "run_ids": ["RUN-*"],
  "constraint_evidence": ["EVID-*"],
  "independent_validation": ["EVID-*"],
  "robustness_or_boundary_check": ["EVID-*"],
  "mechanism_explanation": "关键状态或参数如何导致结果；反常结果如何解释",
  "limitations": ["适用边界"]
}
```

只有 `NUMERIC` 强制给数值、单位和精度。证明、分类、策略和文件任务使用相应证据。现实参数敏感性有意义时执行；不适用时写具体理由，并提供反例、边界、扰动可行性或模型比较中的一种替代检查。

运行证据至少登记命令、环境、版本、输入哈希、退出码、随机种子/非确定性说明、规范化核心结果哈希和日志。`execution-record` 还要逐问登记数学结构与规模、算法匹配依据、简单方法不足之处、参数值/来源/搜索范围、停止准则、资源预算、实际终止原因以及最终残差/gap/迭代数。随机或跨平台输出使用固定种子或预先登记的数值/统计容差复核。失败退出、非有限值、约束失败或核心结果不可重建时不能标记 `VERIFIED`。

## 5. 论文证据合同

阶段三逐问把以下内容连接到同一事实链：

- 正式答案及 `answer_kind`；
- 模型、运行、输出和数字 ID；
- 独立验证或边界证据；
- 正文、摘要、图表和附录位置；
- 适用范围、最优性/因果边界和局限。

论文按主张类型使用状态：官方或外部事实使用已核实的 `FACT`，建模前提明确标为 `ASSUMPTION`，计算结论必须为 `VERIFIED`。不得把尚未验证的 `COMPUTED` 或 `BLOCKED` 内容写成结论。关键数字必须来自 `number-ledger`；摘要、正文、图表、附录和结果文件不得各自手录不同副本。

## 6. 阶段清单与版本

每个阶段使用一个 `stage-manifest.json`，核心字段为：

```json
{
  "schema_version": "1.0",
  "stage": 1,
  "stage_status": "PASS",
  "visibility_status": "USER_VISIBLE_PASS",
  "version_id": "version-index.json 的 SHA-256",
  "inputs": [{"id": "输入 ID", "path": "相对路径", "sha256": "SHA-256"}],
  "artifacts": [{"id": "产物 ID", "path": "相对路径", "sha256": "SHA-256", "status": "VERIFIED"}],
  "reviews": [],
  "review_deliberation": {},
  "gate_checks": [],
  "blockers": []
}
```

路径必须相对工作包且不能越界。`version-index.json` 精确列出被审输入和产物（包括 `execution-record`）的相对路径与 SHA-256；`stage-workflow-record`、评审报告、质询和清单自身不进入被审版本。`version_id` 是该索引文件的 SHA-256。

阶段二和三用 `prior_stage` 连接前序清单路径、哈希和版本。前序版本变化后，后续清单、结果、论文和评分全部失效。

官方题目、规则、模板和原始数据的哈希另存于工作包外的 `trusted-source-manifest`，避免待审包自己改写来源。`official_files` 对每个文件记录稳定 ID、类型、相对信任根路径、SHA-256、覆盖的小问和两名核验者；另记录完整小问 ID 列表以及两名核验者互不相同的 `reviewer_id`/`provider_run_id`。脚本核对真实文件字节、哈希、路径不越界和两次核验覆盖。

## 7. 评审记录

每阶段恰好包含该阶段八个必需角色，并可按题型增加 `ADDITIONAL-*`。每席报告登记：

- `role_id`、独立 `reviewer_id` 和独立 `provider_run_id`；
- `reviewed_version_id` 和带时区的完整 ISO-8601 `sealed_at`；
- 五项各 20 分的理由和冻结证据位置；
- 致命、主要、次要、缺失证据和否决项；
- 未参与修改、未先看他评、只收到允许材料、质询前封存的声明。

时间比较必须解析为真实时刻后统一到 UTC，不能直接比较字符串；日期或无时区时间无效。全部初评封存后才能交叉质询。任一问题未关闭、任一单项不足 20 或任一身份复用，阶段不能 PASS。

## 8. 状态、回退和阻塞

执行期用少量状态描述进度：`NOT_STARTED` 尚未开工，`EXECUTING` 正在高质量执行，`SELF_REVIEW` 执行者预审与修正，`EXPERT_REVIEW` 八席独立评审，`REVISION` 评审后内部返工，`PASS` 同一冻结版本八席全部满分，`BLOCKED` 缺少材料、环境、证据或独立评审能力。这些字面值被清单和门禁脚本按精确字符串校验，写入 JSON 时不得翻译或改写。只有 `PASS` 对应 `USER_VISIBLE_PASS`，其他状态只允许进度汇报。`PASS` 后发现新事实或任何产物变化，回到 `EXECUTING`、`REVISION` 或 `BLOCKED`，不能保留旧分数。

阻塞记录要写清事实、受影响小问/产物、已经尝试的检查、所需材料和恢复后的下一动作。最小结构为：

```json
{
  "schema_version": "1.0",
  "stage": 2,
  "stage_status": "BLOCKED",
  "visibility_status": "BLOCKED",
  "blockers": [{
    "category": "data | rule | environment | evidence | review",
    "reason": "可核实事实",
    "required_material": "解除阻塞所需材料",
    "affected_ids": ["Q1"],
    "resume_condition": "可判定恢复条件"
  }],
  "checkpoint": {
    "saved_at": "完整带时区时间",
    "next_action": "恢复后第一项具体动作",
    "resume_from": "EXECUTING"
  }
}
```

非 `BLOCKED` 的中断恢复检查点用同一结构：`stage_status` 写当前状态，`blockers` 留空；`resume_from` 写恢复后要回到的合法非 `PASS` 状态。用：

`python scripts/check_stage_gate.py --manifest <检查点> --stage <1|2|3> --checkpoint`

验证。即使结构正确，该命令仍返回退出码 1，因为检查点不授予 PASS；输出中的 `checkpoint is valid and resumable` 只表示可以恢复。补齐条件后从最后一个可信版本继续，不无限循环，也不把 `BLOCKED` 伪装成部分完成。
