# 赛马场口径规范（V1）

## 1. 任务类型定义

1. `ultra_short`：15 分钟到 4 小时。  
2. `short`：4 小时到 72 小时。  
3. `medium`：3 天到 14 天。  

说明：当前 demo 以离散 `horizons` 表达提前量，单位默认按采样步长计算。

## 2. 时间与采样

1. 时间列统一字段：`Timestamp`。  
2. 字符串时间格式：`%Y/%m/%d %H:%M`。  
3. 默认采样步长：15 分钟（可在实验配置中注明）。  

## 3. 数据字段口径（首版）

1. 目标列：`Total_Power`（来自 SCADA）。  
2. 预测特征：来自 NWP 与 SCADA 衍生特征（V1 先保留原始读入能力）。  
3. 当前真实数据接入要求：SCADA 与 NWP 必须可按 `Timestamp` 对齐。  

## 4. 指标口径

1. 主指标：`MAE`。  
2. 辅指标：`RMSE`。  
3. 后续计划加入：`nMAE`、`MAPE`、分位数与稳定性指标。  

## 5. 复现最小信息

每次运行必须记录：

1. `dataset_version`  
2. `horizons`  
3. 模型名与参数  
4. 运行输出目录  
5. 数据质量快照（`dataset_profile.json`）  

## 6. 配置约束（当前实现）

1. 若 `experiment.data_source=synthetic`，使用内置合成序列。  
2. 若 `experiment.data_source=real_csv`，必须提供：
   - `data.scada_csv`
   - `data.nwp_csv`
   - `data.timestamp_col`
   - `data.target_col`

