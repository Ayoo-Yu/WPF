# 风电功率预测赛马场设计文档（MVP v1）

## 1. 背景与目标

你当前的核心痛点：

- 同时维护多个风电场、多个预测任务（超短期/短期/中期），实验组合爆炸。
- 算法与超参数很多，每次换场站或任务都要重复回测，效率低。
- 难以快速回答“在某个场站+某个任务下，当前最优方法是什么”。
- 实验结果分散，复现困难，容易遗漏细节与对比维度。

赛马场系统（Racecourse）的目标是：

- 标准化实验定义与运行流程。
- 一键批量回测，多算法公平对比。
- 可复现、可追踪、可审计（数据版本/代码版本/参数/指标）。
- 自动生成分层排行榜，支持“快速选型”与“稳定性评估”。

---

## 2. 设计原则

- **可复现优先**：任何结果都能重跑出来。
- **插件化算法**：新增算法不改核心调度逻辑。
- **配置驱动**：实验通过配置文件定义，不靠手改脚本。
- **分层评估**：不只看全局均值，要看场站/季节/风况/提前量分层表现。
- **先MVP后扩展**：先解决 80% 高频问题，再加高级能力（AutoML、在线学习等）。

---

## 3. 范围定义（MVP）

### 3.1 支持对象

- 多风电场。
- 多预测任务：
  - 超短期（例如 15min~4h）
  - 短期（例如 4h~72h）
  - 中期（例如 3d~14d）
- 多算法（统计模型、机器学习、深度学习均可接入）。

### 3.2 MVP功能

- 数据集注册与版本管理（最少做到“版本号 + 时间戳 + 生成说明”）。
- 统一算法接口：`fit` / `predict`。
- 实验配置管理（YAML）。
- 批量回测调度（支持并行）。
- 指标计算与结果落库。
- 排行榜（按场站、任务、指标排序）。
- 实验追踪页面（最简可先做命令行 + Markdown/CSV 报告）。

---

## 4. 总体架构

```text
┌──────────────────────────┐
│      Experiment Config   │  (YAML)
└──────────────┬───────────┘
               │
               ▼
┌──────────────────────────┐
│      Orchestrator        │  解析配置/生成任务/调度并行
└──────────────┬───────────┘
               │
   ┌───────────┴───────────┐
   ▼                       ▼
┌──────────────┐      ┌──────────────┐
│ Data Manager │      │ Model Runner │
│ 数据切片/特征 │      │ 训练/预测/记录 │
└──────┬───────┘      └──────┬───────┘
       │                     │
       ▼                     ▼
┌────────────────────────────────────┐
│ Evaluator + Metrics + Result Store │
└────────────────┬───────────────────┘
                 ▼
         ┌───────────────┐
         │ Leaderboard   │
         │ 报告与对比视图 │
         └───────────────┘
```

---

## 5. 关键数据模型

建议最少维护以下实体（SQLite/PostgreSQL 均可）：

### 5.1 `dataset_versions`

- `dataset_version_id`
- `site_id`
- `time_range_start`, `time_range_end`
- `schema_hash`
- `feature_spec_version`
- `created_at`
- `notes`

### 5.2 `experiments`

- `experiment_id`
- `name`
- `task_type`（ultra_short / short / medium）
- `horizon_spec`（预测提前量列表）
- `split_strategy`（rolling / blocked / expanding）
- `dataset_version_id`
- `created_by`
- `created_at`

### 5.3 `runs`

- `run_id`
- `experiment_id`
- `site_id`
- `model_name`
- `model_version`
- `hyperparams_json`
- `random_seed`
- `code_commit`
- `status`
- `start_time`, `end_time`
- `artifact_path`

### 5.4 `metrics`

- `run_id`
- `metric_name`（MAE/RMSE/MAPE/nMAE/Pinball等）
- `metric_value`
- `segment_key`（overall/season/wind_bin/horizon）
- `segment_value`

---

## 6. 统一算法接口（建议）

```python
class ForecastModel:
    def fit(self, train_df, valid_df, config: dict) -> None:
        ...

    def predict(self, future_df) -> "pd.DataFrame":
        """
        返回列至少包含:
        - timestamp
        - y_pred
        可选:
        - y_pred_p10/y_pred_p50/y_pred_p90 (概率预测)
        """
        ...

    def save(self, path: str) -> None:
        ...

    def load(self, path: str) -> "ForecastModel":
        ...
```

要求：

- 输入输出字段标准化。
- 每个模型必须可序列化（便于复现与部署）。
- 模型内部可自由实现，但接口必须一致。

---

## 7. 实验配置模板（YAML）

```yaml
experiment:
  name: "siteA_short_term_baseline"
  task_type: "short"
  sites: ["siteA"]
  dataset_version: "ds_2026_02_01_v1"
  split:
    strategy: "rolling"
    train_days: 180
    valid_days: 30
    test_days: 30
    step_days: 30
  horizons: [1, 2, 4, 8, 16, 24]  # 小时
  metrics: ["MAE", "RMSE", "nMAE"]
  seed: 42

models:
  - name: "persistence"
    params: {}
  - name: "lightgbm"
    params_grid:
      num_leaves: [31, 63]
      learning_rate: [0.03, 0.1]
      n_estimators: [300, 800]
  - name: "lstm"
    params_grid:
      hidden_size: [64, 128]
      dropout: [0.1, 0.3]
      lr: [0.001]
```

---

## 8. 评估体系（必须先定）

建议至少包含：

- 点预测指标：`MAE`, `RMSE`, `nMAE`（推荐加归一化便于跨场站比较）。
- 分提前量评估：每个 horizon 单独打分。
- 分场景评估：
  - 季节（春夏秋冬）
  - 风速区间（低/中/高）
  - 限电时段（如可标注）

评估输出建议：

- 主榜单：每个“场站+任务类型”Top N。
- 稳定性榜单：各分层分位数表现（避免“平均值好但波动大”）。

---

## 9. 工作流（端到端）

1. 数据准备并登记 `dataset_version`。  
2. 编写实验 YAML（定义任务、切分、模型和搜索空间）。  
3. Orchestrator 解析配置并生成回测任务矩阵。  
4. 并行执行训练与预测，记录 `runs`。  
5. Evaluator 计算指标并写入 `metrics`。  
6. 生成排行榜与实验报告（CSV + Markdown + 可视化）。  
7. 标记最佳配置进入“候选模型库”用于新场站快速迁移。  

---

## 10. 推荐项目结构

```text
WPF/
  docs/
    wind-power-racecourse-design.md
  configs/
    experiments/
  data/
    raw/
    processed/
  src/
    core/
      orchestrator.py
      runner.py
      evaluator.py
      leaderboard.py
    data/
      dataset_registry.py
      splitter.py
      features.py
    models/
      base.py
      persistence.py
      lightgbm_model.py
      lstm_model.py
    utils/
      io.py
      logger.py
  outputs/
    runs/
    reports/
  tests/
```

---

## 11. 两周MVP里程碑（建议）

### Week 1

- 完成数据版本登记与切分模块。
- 完成统一模型接口与2-3个基线模型接入（Persistence + LightGBM + 1个深度学习）。
- 打通单场站单任务的完整回测流程。

### Week 2

- 增加超参数网格搜索与并行执行。
- 完成指标落库与排行榜输出。
- 支持多场站批量运行。
- 产出首版“模型选择报告模板”。

---

## 12. 风险与防坑清单

- 数据泄漏：特征构造必须严格时间因果。
- 切分不一致：不同模型必须使用完全一致的训练/验证/测试窗口。
- 指标偏差：MAPE 在低功率时段不稳定，需搭配 MAE/nMAE。
- 过拟合排行榜：需要跨时间窗稳定性验证，不只看单次最优。
- 复现失败：必须固定随机种子并记录代码 commit 与依赖版本。

---

## 13. 下一步落地建议

- 先确定 `task_type` 和 `horizons` 的统一标准（写成常量表）。
- 先实现 `Persistence` 作为基线，确保评估链路先跑通。
- 优先做“可复现与可追踪”，再追求复杂模型。

这份文档可作为 v1 基线，后续每次改架构时在文档尾部新增“变更记录（changelog）”。
