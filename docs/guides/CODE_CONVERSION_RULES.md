# A9950 Code转换规则文档

## 文档说明
本文档详细记录了A9950项目中所有code之间的转换关系，用于在其他项目中复现相同的转换逻辑。

---

## 目录
1. [转换执行顺序（重要）](#转换执行顺序重要)
2. [产品分类定义](#产品分类定义)
3. [辅助Code转换](#辅助code转换)
4. [小尺寸产品Judge转换](#小尺寸产品judge转换)
5. [M1→T1转换](#m1t1转换)
6. [M2_SP_PI→AS_CV_PI转换](#m2_sp_pias_cv_pi转换)
7. [特殊产品处理](#特殊产品处理)
8. [阈值过滤逻辑](#阈值过滤逻辑)
9. [Judge优先级](#judge优先级)
10. [Code优先级](#code优先级)

---

## 转换执行顺序（重要）

### 为什么转换顺序很重要？

某些转换会改变code的judge类型，从而**阻止**后续转换的执行。例如：
- 小产品的 `M2_SP_PI_P` 先转成 `M2_SP_PI_G`（judge变为'G'）
- 后续的 `P/L → Q` 转换就不会再执行（因为judge已经是'G'，不是'P'或'L'）

---

### 完整转换执行顺序

#### 阶段1：result_df预处理（主函数中，576-610行）

| 顺序 | 转换 | 代码位置 | 说明 |
|------|------|---------|------|
| 1.1 | 横线转下划线 | 577行 | `P1-XX-BV-P` → `P1_XX_BV_P` |
| 1.2 | 移除M1_XX_MK_R2 | 580行 | 删除 `M1_XX_MK_R2` |
| 1.3 | 转人工产品BV处理 | 584-586行 | 产品在P_TO_RENGONG + 主code是P1_XX_BV_P → conf=0.1 |
| **1.4** | **小产品M2_SP_PI_P→G** | **588-596行** | **小产品 M2_SP_PI_P → M2_SP_PI_G** |
| 1.5 | M1_SP_PI_P2 → M1_SP_PI_P | 599-604行 | 置信度设为0.1 |
| 1.6 | M2_SP_PI_P2 → M2_SP_PI_P | 606-610行 | 保持原置信度 |

**关键点**：
- 第1.4步（588行）在**get_judge函数之前**执行
- 小产品的 `M2_SP_PI_P` 转成 `M2_SP_PI_G` 后，judge变为'G'
- 后续第138行的 `P/L → Q` 转换条件不满足，不会再执行

---

#### 阶段2：get_judge函数处理（118-185行）

| 顺序 | 转换 | 代码位置 | 说明 |
|------|------|---------|------|
| 2.1 | 阈值判断 | 90-100行 | code_judge_conf函数，低于阈值标记为'other' |
| 2.2 | 阳化产品BD/BS处理 | 133-134行 | 置信度设为0.1 |
| **2.3** | **小产品P/L→Q/S/G** | **138-148行** | **小产品 P/L judge 转换** |
| 2.4 | 产品103 P/L→Q | 150-153行 | 产品103的 P/L → Q |
| 2.5 | M1_SP_PI→T1_SP_PI | 155-160行 | M1_TO_T1产品转换 |
| 2.6 | M2_SP_PI→AS_CV_PI | 162-171行 | 非AS_TO_M2产品转换 |

**关键点**：
- 第2.3步（138行）只处理 judge='P' 或 'L' 的code
- 如果code在第1.4步已经转成'G' judge，不会再走P/L→Q转换

---

#### 阶段3：特殊产品处理（主函数中，613-683行）

| 顺序 | 转换 | 代码位置 | 说明 |
|------|------|---------|------|
| 3.1 | 9300/9950焦黑孔处理 | 613-618行 | 检测到P1_XX_BV_P_not时过滤PI |
| 3.2 | DATA线PI数量卡控 | 620-623行 | PI数量>5 → conf=0.1 |
| 3.3 | 大产品PI/IR过滤 | 625-634行 | 大产品 M1_SP_PI_P >0.25, M2_PH_IR_P >0.2 |
| 3.4 | 大产品BV→PF | 637-646行 | 大产品 P1_XX_BV_P/G → PF_XX_BV_P/G |
| 3.5 | QK_G→QK_P | 648-655行 | M1_PH_QK_G → M1_PH_QK_P |
| 3.6 | UN转人工 | 658-663行 | T3_XX_UN_G → conf=0.111 |
| 3.7 | 238/270产品VN过滤 | 666-671行 | P1_PH_VN_P 置信度>0.2 |
| 3.8 | BD统一转M2_DE_BD_G | 673-678行 | M1/M2_DE_BD_G → M2_DE_BD_G |
| 3.9 | 删除辅助code | 682行 | 删除additional_code, P1_XX_BV_P_not |

---

#### 阶段4：阈值过滤（686-691行）

| 顺序 | 转换 | 代码位置 | 说明 |
|------|------|---------|------|
| 4.1 | model_ok_threshold过滤 | 686-691行 | 低于阈值的code被过滤 |

---

#### 阶段5：灰阶图处理（694-750行）

| 顺序 | 转换 | 代码位置 | 说明 |
|------|------|---------|------|
| 5.1 | GRAY_IR → M1_XX_MK_R | 694-702行 | 灰阶图MARK检测 |
| 5.2 | CV十字Mark检测 | 715-745行 | 未检测到GRAY_IR时执行CV检测 |

---

### 转换冲突示例

#### 示例1：小产品 M2_SP_PI_P 的转换路径

**产品**：H4A067HDF13（pro=067，小产品）

| 步骤 | 原code | 转换 | 结果code | judge |
|------|--------|------|---------|-------|
| 1.4 | M2_SP_PI_P | 588行转换 | M2_SP_PI_G | G |
| 2.3 | M2_SP_PI_G | 138行条件检查 | **不转换**（judge='G'，不是'P'/'L'） | G |

**最终结果**：`M2_SP_PI_G`（不是 `M2_SP_PI_Q`）

---

#### 示例2：小产品 M1_XX_UO_P 的转换路径

**产品**：H4A067HDF13（pro=067，小产品）

| 步骤 | 原code | 转换 | 结果code | judge |
|------|--------|------|---------|-------|
| 2.3 | M1_XX_UO_P | 138行（特殊列表） | M1_XX_UO_G | G |

**最终结果**：`M1_XX_UO_G`

**说明**：`M1_XX_UO_P` 在特殊列表中，转成'G' judge，不是'Q'

---

#### 示例3：中产品 M2_SP_PI_P 的转换路径

**产品**：H4A101HDF13（pro=101，不在small_products中）

| 步骤 | 原code | 转换 | 结果code | judge |
|------|--------|------|---------|-------|
| 1.4 | M2_SP_PI_P | **不转换**（不是小产品） | M2_SP_PI_P | P |
| 2.3 | M2_SP_PI_P | **不转换**（不是小产品） | M2_SP_PI_P | P |
| 2.6 | M2_SP_PI_P | **不转换**（101在AS_TO_M2中） | M2_SP_PI_P | P |

**最终结果**：`M2_SP_PI_P`

---

#### 示例4：大产品 M2_SP_PI_P 的转换路径

**产品**：H4A238HDF13（pro=238，大产品，不在AS_TO_M2中）

| 步骤 | 原code | 转换 | 结果code | judge |
|------|--------|------|---------|-------|
| 2.6 | M2_SP_PI_P | 162行转换 | AS_CV_PI_P | P |

**最终结果**：`AS_CV_PI_P`

---

#### 示例5：270产品 M1_SP_PI_P 的转换路径

**产品**：H4A270FDF10（pro=270，在M1_TO_T1中）

| 步骤 | 原code | 转换 | 结果code | judge |
|------|--------|------|---------|-------|
| 2.5 | M1_SP_PI_P | 155行转换 | T1_SP_PI_P | P |

**最终结果**：`T1_SP_PI_P`

---

### 转换阻止规则总结

| 先执行的转换 | 阻止的转换 | 原因 |
|-------------|-----------|------|
| 588行：小产品 M2_SP_PI_P → G | 138行：小产品 P/L → Q | judge已变为'G'，不是'P'/'L' |
| 138行：转成'G' | 138行：转成'Q' | judge已变为'G'，不是'P'/'L' |
| 138行：转成'Q' | 138行：转成'S' | code已变更，不再匹配关键字判断 |
| 155行：M1→T1 | 162行：M2→AS | code已变成T1，不再匹配M2_SP_PI |
| 162行：M2→AS | 无 | AS_CV_PI不再参与后续转换 |

---

### 关键转换决策树

```
模型检测到 M2_SP_PI_P
    │
    ├─ 产品在 small_products？
    │   ├─ 是 → 执行588行：M2_SP_PI_P → M2_SP_PI_G
    │   │        judge变为'G'，后续138行P/L→Q不执行 ✓
    │   │
    │   └─ 否 → 保持 M2_SP_PI_P
    │             进入get_judge函数
    │
    ├─ 执行138行：小产品 P/L → Q/S/G
    │   ├─ code在特殊列表（UO/SA/T3_SP_PI等）？
    │   │   └─ 是 → 转成'G' judge
    │   │
    │   ├─ code包含CK/GC/GD/SC/AC/ES关键字？
    │   │   └─ 是 → 转成'S' judge
    │   │
    │   └─ 其他 → 转成'Q' judge
    │
    └─ 执行162行：M2_SP_PI → AS_CV_PI
        ├─ 产品在 AS_TO_M2_products？
        │   └─ 是 → 保持 M2_SP_PI_*
        │
        └─ 否 → M2_SP_PI_* → AS_CV_PI_*
```

---

## 产品分类定义

### 产品信息提取规则
```python
# 从完整产品型号中提取产品代码
product = "H4A067HDF13"  # 完整产品型号
pro = product[3:6]       # 提取第4-6位，如 "067"
```

### 产品分类列表

#### 小尺寸产品 (small_products)
```
["020", "047", "050", "055", "056", "057", "058", "059", "060", "061", "062", "063",
 "064", "065", "066", "067", "068", "069", "070", "071", "072", "073", "074", "075",
 "076", "077", "078", "079", "080", "081", "082", "083", "084", "085", "086", "087",
 "088", "089", "090", "091", "092", "093", "094", "095"]
```

#### 大尺寸产品 (big_products)
```
["500", "550", "650", "860"]
```

#### AS层产品 (AS_TO_M2_products) - 保持M2_SP_PI不变
```
["020", "047", "050", "055", "056", "057", "058", "059", "060", "061", "062", "063",
 "064", "065", "066", "067", "068", "069", "070", "071", "072", "073", "074", "075",
 "076", "077", "078", "079", "080", "081", "082", "083", "084", "085", "086", "087",
 "088", "089", "090", "091", "092", "093", "094", "095", "101", "109", "116", "140", "156"]
```

#### M1→T1转换产品 (M1_TO_T1_products)
```
["238", "270", "430", "156", "215", "245"]
```

#### 阳化产品 (yanghua_poducts)
```
["H4A145QDF02", "H4A245QDF01", "H4A270QDF01", "H4A270QDF02", "H4A270QDF03",
 "H4A270QDF05", "H4A270QDF06", "H4A270UDF02"]
```

#### 转人工产品 (P_TO_RENGONG)
```
["H4A430FDA07", "H4A215FDF02"]
```

---

## 辅助Code转换

### 1. M1_SP_PI_P2 → M1_SP_PI_P
**代码位置**: predictor.py:599-604
```python
M1_SP_PI_P2['code_name'] = 'M1_SP_PI_P'
M1_SP_PI_P2['confidence'] = 0.1
```
- **条件**: 无条件，所有产品
- **转换**: M1_SP_PI_P2 → M1_SP_PI_P
- **置信度**: 设为 0.1（转人工）

---

### 2. M2_SP_PI_P2 → M2_SP_PI_P
**代码位置**: predictor.py:606-610
```python
M2_SP_PI_P2['code_name'] = 'M2_SP_PI_P'
```
- **条件**: 无条件，所有产品
- **转换**: M2_SP_PI_P2 → M2_SP_PI_P
- **置信度**: 保持原置信度

---

### 3. M1_PH_QK_G → M1_PH_QK_P
**代码位置**: predictor.py:648-655
```python
QK['code_name'] = 'M1_PH_QK_P'
if pro in big_products:
    QK = QK[QK['confidence'] > 0.25]
else:
    QK = QK[QK['confidence'] > 0.1]
```
- **条件**: 无条件，所有产品
- **转换**: M1_PH_QK_G → M1_PH_QK_P
- **大产品**: 置信度 > 0.25 保留
- **小/中产品**: 置信度 > 0.1 保留

---

### 4. T3_XX_UN_G → T3_XX_UN_G (转人工)
**代码位置**: predictor.py:658-663
```python
UN['confidence'] = 0.111
```
- **条件**: 无条件，所有产品
- **code**: T3_XX_UN_G / T3_XX_UN_G2 → T3_XX_UN_G
- **置信度**: 设为 0.111（转人工）

---

### 5. P1_XX_BV_P/G → PF_XX_BV_P/G (大产品)
**代码位置**: predictor.py:637-646
```python
if result_df.loc[0,'code_name'] == 'P1_XX_BV_P':
    result_df['code_name'] = 'PF_XX_BV_P'
else:
    result_df['code_name'] = 'PF_XX_BV_G'
result_df['confidence'] = 0.2
```
- **条件**: 大产品 (big_products) + 最高置信度是 P1_XX_BV_P 或 P1_XX_BV_G
- **转换**:
  - P1_XX_BV_P → PF_XX_BV_P
  - P1_XX_BV_G → PF_XX_BV_G
- **置信度**: 设为 0.2（转人工）

---

### 6. M1_DE_BD_G / M2_DE_BD_G → M2_DE_BD_G
**代码位置**: predictor.py:673-678
```python
BD = BD[BD['confidence'] > 0.15]
BD['code_name'] = 'M2_DE_BD_G'
```
- **条件**: 无条件，所有产品
- **转换**:
  - M1_DE_BD_G → M2_DE_BD_G
  - M2_DE_BD_G → M2_DE_BD_G (保持)
- **置信度**: > 0.15 保留

---

### 7. 灰阶图MARK处理
**代码位置**: predictor.py:694-750

#### 7.1 GRAY_IR → M1_XX_MK_R
```python
if 'GRAY_IR' in result_df or 'M2_XX_SC_S' in result_df:
    result_df['code_name'] = 'M1_XX_MK_R'
    result_df['confidence'] = 0.1
```

#### 7.2 CV检测十字Mark
如果未检测到GRAY_IR和M2_XX_SC_S，但检测到M1_XX_MK_R：
- 置信度 > 0.52: 保留 M1_XX_MK_R（转人工）
- 置信度 ≤ 0.52: 如果有 H4_XX_ZQ_G 则输出，否则转人工

#### 7.3 无任何检测
- 执行CV算法检测十字Mark
- 检测到: 输出 H4_XX_ZQ_G（置信度0.9）
- 未检测到: 输出 M1_XX_MK_R（转人工）

---

## 小尺寸产品Judge转换

### 转换规则
**代码位置**: predictor.py:138-148

```python
if pro in small_products and judge in ['P', 'L']:
    if code in [特殊列表]:
        code = code[:-1] + 'G'  # 转成G judge
        judge = 'G'
    elif 'CK' in code or 'GC' in code or 'GD' in code or 'SC' in code or 'AC' in code or 'ES' in code:
        code = code[:-1] + 'S'  # 转成S judge
        judge = 'S'
    else:
        code = code[:-1] + 'Q'  # 转成Q judge
        judge = 'Q'
```

### 转成G judge的特殊Code列表
```
['M1_XX_UO_P', 'M1_XX_UO_L', 'T1_XX_UO_P', 'T1_XX_UO_L',
 'M2_XX_UO_P', 'M2_XX_UO_L', 'M2_XX_SA_P', 'AS_CV_SA_P',
 'P1_CV_SA_P', 'T3_XX_UO_P', 'T3_XX_UO_L', 'AS_XX_UO_P',
 'T3_SP_PI_P']
```

### 转成S judge的Code（包含指定关键字）
```
包含以下关键字的code转成S judge:
'CK', 'GC', 'GD', 'SC', 'AC', 'ES'
```

### 转成Q judge的Code
```
其他所有小尺寸产品的 P/L judge 转成 Q judge
```

---

## 小尺寸产品M2_SP_PI特殊处理

### M2_SP_PI_P → M2_SP_PI_G (小产品)
**代码位置**: predictor.py:588-596
```python
if pro in small_products:
    M2_SP_PI_P['code_name'] = 'M2_SP_PI_G'
    if pro in ['070', '080', '090']:
        M2_SP_PI_P['confidence'] = 0.1
```
- **条件**: 小尺寸产品 (small_products)
- **转换**: M2_SP_PI_P → M2_SP_PI_G
- **特殊产品** (070, 080, 090): 置信度设为 0.1（转人工）

---

## M1→T1转换

### M1_SP_PI_* → T1_SP_PI_*
**代码位置**: predictor.py:155-160
```python
if pro in M1_TO_T1_products and 原code是M1_SP_PI_*:
    if pro == '156' and product != 'H4A156FDF04':
        pass  # 不转换
    else:
        code = 'T1_' + code[3:]  # M1_XX_PI_P → T1_SP_PI_P
```

### 转换示例
| 原code | 产品 | 转换后code |
|--------|------|-----------|
| M1_SP_PI_P | 238/270/430/156/215/245 | T1_SP_PI_P |
| M1_SP_PI_G | 238/270/430/156/215/245 | T1_SP_PI_G |
| M1_SP_PI_S | 238/270/430/156/215/245 | T1_SP_PI_S |

### 特殊情况
- 产品156且型号不是H4A156FDF04: 不转换，保持M1_SP_PI_*

---

## M2_SP_PI→AS_CV_PI转换

### 转换规则
**代码位置**: predictor.py:162-171
```python
if pro not in AS_TO_M2_products and code in ['M2_SP_PI_G', 'M2_SP_PI_P', 'M2_SP_PI_S', 'M2_SP_PI_Q']:
    if code == 'M2_SP_PI_G':
        code = 'AS_CV_PI_G'
    if code == 'M2_SP_PI_P':
        code = 'AS_CV_PI_P'
    if code == 'M2_SP_PI_S':
        code = 'AS_CV_PI_S'
    if code == 'M2_SP_PI_Q':
        code = 'AS_CV_PI_Q'
```

### 转换条件
- **产品不在AS_TO_M2_products列表中**（即不是020-156的产品）

### 转换示例
| 原code | 产品类型 | 转换后code |
|--------|---------|-----------|
| M2_SP_PI_G | 大/中尺寸 | AS_CV_PI_G |
| M2_SP_PI_P | 大/中尺寸 | AS_CV_PI_P |
| M2_SP_PI_S | 大/中尺寸 | AS_CV_PI_S |
| M2_SP_PI_Q | 大/中尺寸 | AS_CV_PI_Q |

### 不转换的情况
- **产品在AS_TO_M2_products中**: 保持 M2_SP_PI_*

---

## 特殊产品处理

### 1. 产品103特殊处理
**代码位置**: predictor.py:150-153
```python
if pro in ['103'] and judge in ['P', 'L']:
    code = code[:-1] + 'Q'
    judge = 'Q'
```
- **条件**: 产品103
- **转换**: P/L judge → Q judge

---

### 2. 产品238/270 VN过检处理
**代码位置**: predictor.py:666-671
```python
if pro in ['238', '270']:
    VN = result_df[result_df['code_name'] == 'P1_PH_VN_P']
    VN = VN[VN['confidence'] > 0.2]
```
- **条件**: 产品238或270
- **code**: P1_PH_VN_P
- **置信度**: > 0.2 保留

---

### 3. 阳化产品BD/BS特殊处理
**代码位置**: predictor.py:133-134
```python
if code in ['M2_DE_BS', 'M2_DE_BD'] and product in yanghua_poducts:
    code_confidence = 0.1
```
- **条件**: 阳化产品 + code是M2_DE_BS或M2_DE_BD
- **置信度**: 设为 0.1（转人工）

---

### 4. 转人工产品BV处理
**代码位置**: predictor.py:584-586
```python
if product in p_to_rengong and result_df.loc[0,'code_name'] == 'P1_XX_BV_P':
    result_df['confidence'] = 0.1
```
- **条件**: 产品在P_TO_RENGONG中 + 主code是P1_XX_BV_P
- **置信度**: 设为 0.1（转人工）

---

### 5. 9300/9950产品焦黑孔处理
**代码位置**: predictor.py:613-618
```python
if 'P1_XX_BV_P_not' in result_df:
    PI = result_df[result_df['code_name'].isin(['T3_SP_PI_P', 'AS_CV_PI_P', 'P1_XX_BV_P', 'M2_SP_PI_P'])]
    PI = PI[PI['confidence'] > 0.5]
```
- **条件**: 检测到P1_XX_BV_P_not
- **处理**: 过滤PI相关code，置信度 > 0.5 保留

---

### 6. 大产品M1_SP_PI_P/M2_PH_IR_P过滤
**代码位置**: predictor.py:625-634
```python
if pro in big_products:
    PI = result_df[result_df['code_name'] == 'M1_SP_PI_P']
    PI = PI[PI['confidence'] > 0.25]

    IR = result_df[result_df['code_name'] == 'M2_PH_IR_P']
    IR = IR[IR['confidence'] > 0.2]
```
- **条件**: 大产品
- **M1_SP_PI_P**: 置信度 > 0.25 保留
- **M2_PH_IR_P**: 置信度 > 0.2 保留

---

### 7. DATA线PI数量卡控
**代码位置**: predictor.py:620-623
```python
DATA_PI = result_df[result_df['code_name'].isin(['T3_SP_PI_P','M2_SP_PI_P', 'AS_CV_PI_P','M2_XX_UO_P'])]
if DATA_PI.shape[0] > 5:
    result_df['confidence'] = 0.1
```
- **条件**: DATA线上PI数量 > 5
- **置信度**: 设为 0.1（转人工）

---

### 8. PI+UO小颗粒被大PO过滤
**代码位置**: predictor.py:192-200
```python
if 'T3_XX_PO_G' in all_code:
    PO_SIZE = max(PO的尺寸)
    PI_UO_SIZE = max(PI_UO的尺寸)
    if PO_SIZE > 50 and PI_UO_SIZE < 20:
        过滤掉PI_UO
```
- **条件**: 同时检出大尺寸PO(>50)和小尺寸PI/UO(<20)
- **处理**: 过滤掉小尺寸的PI和UO

---

## 阈值过滤逻辑

### model_other_threshold（低置信度转人工）
**代码位置**: predictor.py:90-100

```python
def code_judge_conf(code, confidence, other_code):
    try:
        code_threshold = model_other_threshold[code]
        if confidence > code_threshold:
            return code  # 达到阈值，保留
        else:
            return other_code  # 未达到，标记为'other'
    except:
        return code  # 无阈值定义，保留
```

### 阈值过滤后处理
**代码位置**: predictor.py:215-220
```python
all_code_other = all_code[all_code['other'] == 'other']
all_code_code = all_code[all_code['other'] != 'other']
if all_code_code.shape[0] > 0:
    all_code = all_code_code  # 只保留达到阈值的
else:
    all_code = all_code_other  # 全部未达到，保留全部
```

### 重要阈值示例
| Code | 阈值 |
|------|------|
| M2_SP_PI_G/P/S | 0.75 |
| M1_SP_PI_G/P/S | 0.75 |
| AS_CV_PI_G | 0.5 |
| AS_CV_PI_P | 0.6 |
| M1_DE_BD_G/P/S | 0.4 |
| M2_DE_BD_G/P/S | 0.4 |
| M2_DE_BS_G | 0.45 |
| M2_DE_BS_P/S | 0.5 |
| NP_XX_UN_G | 0.75 |
| NP_XX_UN_P | 0.4 |
| P1_XX_BV_P | 0.45 |
| P1_XX_BV_G | 0.5 |

### 无阈值Code
未在model_other_threshold中定义的code，默认保留不过滤。

**重要**: M2_SP_PI_Q 等code没有阈值定义，即使置信度很低也会保留。

---

### model_ok_threshold（OK阈值）
**代码位置**: predictor.py:686-691

```python
for code in model_ok_threshold.keys():
    code_threshold = model_ok_threshold[code]
    code_result = result_df[result_df['code_name'] == code]
    code_result = code_result[code_result['confidence'] > code_threshold]
```

### OK阈值示例
| Code | 阈值 |
|------|------|
| T3_XX_UN_G | 0.2 |
| AS_CV_FB_G | 0.2 |
| P1_CV_FB_G | 0.2 |
| T3_SP_FB_G | 0.2 |
| T3_PH_W1_G | 0.15 |
| T3_PH_W3_G | 0.15 |
| M1_XX_SC_S | 0.2 |
| M2_DE_BN_P | 0.2 |

---

## Judge优先级

### 优先级顺序（从高到低）
```
S (Severe) > Q (Question/ManualReview) > D (Defect) > R (Repair) > L (Light) > P (Pass) > G (Good)
```

### 优先级应用规则
1. 按优先级从高到低处理judge
2. 高优先级judge内有输出，则忽略低优先级judge
3. 同judge内按code优先级输出

---

## Code优先级

### 优先级列表（从高到低）
```
["QK", "CK", "GC", "GC1", "SC", "SC1", "AC", "AC1", "SP", "SP1", "ES", "ES1", "VN", "BV", "PB",
 "BL", "PE", "FB", "FB1", "PL", "PL1", "OP", "OD", "CO", "CO1", "PP", "FC", "UE", "UE1",
 "OE", "OE1", "MB", "QK1", "IU", "IU1", "SD", "SD1", "BN", "BP", "IR", "IR1", "LR", "CR",
 "PI", "CP", "PO", "SA", "SA1", "BA", "BB", "BC", "F1", "F2", "F21", "U1", "U2", "UC", "ID",
 "MK", "PS", "MD", "AD", "RP", "SB", "PC", "RB", "MS", "GB", "GD", "C1", "BU", "BS", "BD",
 "QD", "UR", "UG", "BW", "UW", "BO", "UO", "UO1", "WR", "UN", "UN1", "LY", "NF", "LD", "DE",
 "DF", "RF", "RF1", "RG", "ZQ"]
```

### 应用规则
- 同judge内，按code优先级输出
- 选择优先级最高且置信度最高的code作为主code

---

## 转换流程总结

### 完整转换流程（按执行顺序）

```
1. 模型输出原始code
   ↓
2. result_df预处理阶段（576-610行）
   2.1 横线转下划线 (577行)
   2.2 移除M1_XX_MK_R2 (580行)
   2.3 转人工产品BV处理 (584-586行)
   2.4 ⚠️ 小产品M2_SP_PI_P→G (588-596行) 【关键：阻止后续P/L→Q】
   2.5 M1_SP_PI_P2→M1_SP_PI_P (599-604行)
   2.6 M2_SP_PI_P2→M2_SP_PI_P (606-610行)
   ↓
3. get_judge函数处理（118-185行）
   3.1 遍历每个code，提取judge
   3.2 阈值判断 (90-100行)
       - 低于阈值 → 标记为'other'
       - 高于阈值/无阈值 → 保留
   3.3 阳化产品BD/BS处理 (133-134行)
   3.4 ⚠️ 小产品P/L→Q/S/G转换 (138-148行) 【关键：judge变更后不再参与】
       - 特殊列表（UO/SA/T3_SP_PI等） → G
       - 含CK/GC/GD/SC/AC/ES关键字 → S
       - 其他 → Q
   3.5 产品103 P/L→Q (150-153行)
   3.6 ⚠️ M1_SP_PI→T1_SP_PI (155-160行) 【关键：code变更后不再匹配M2规则】
   3.7 ⚠️ M2_SP_PI→AS_CV_PI (162-171行) 【关键：只在非AS_TO_M2产品中执行】
   3.8 返回all_code DataFrame
   ↓
4. 特殊产品处理阶段（613-683行）
   4.1 9300/9950焦黑孔处理 (613-618行)
   4.2 DATA线PI数量卡控 (620-623行)
   4.3 大产品PI/IR过滤 (625-634行)
   4.4 大产品BV→PF (637-646行)
   4.5 QK_G→QK_P (648-655行)
   4.6 UN转人工 (658-663行)
   4.7 238/270产品VN过滤 (666-671行)
   4.8 BD统一转M2_DE_BD_G (673-678行)
   4.9 删除辅助code (682行)
   ↓
5. 阈值过滤阶段（686-691行）
   5.1 model_ok_threshold过滤
   ↓
6. 灰阶图处理阶段（694-750行，如果是灰阶图）
   6.1 GRAY_IR→M1_XX_MK_R (694-702行)
   6.2 CV十字Mark检测 (715-745行)
   ↓
7. 阈值过滤后处理（215-220行）
   - 过滤掉'other'标记的code
   - 如果全部是'other'，保留全部
   ↓
8. Judge优先级处理（223-273行）
   S > Q > D > R > L > P > G
   ↓
9. Code优先级处理
   同judge内按code优先级输出
   ↓
10. 最终输出
```

---

### 转换决策流程图

```
                    ┌─────────────────┐
                    │  模型输出code   │
                    └────────┬────────┘
                             │
                ┌────────────┴────────────┐
                │ 产品在small_products？  │
                └────────────┬────────────┘
                     ┌───────┴───────┐
                    是               否
                     │               │
            ┌────────┴────────┐      │
            │ code是M2_SP_PI_P?│      │
            └────────┬────────┘      │
         ┌───────────┴───────────┐   │
        是                      否   │
         │                       │    │
    ┌────┴────┐              ┌────┴────┐
    │转成M2_  │              │进入get_ │
    │SP_PI_G  │              │judge函数│
    │(588行)  │              │(118行)  │
    └────┬────┘              └────┬────┘
         │                         │
    judge='G'                 ┌────┴────────┐
         │                     │code在特殊列表│
         │                     │(UO/SA/...)？ │
         │                     └────┬────────┘
         │                  ┌──────┴──────┐
         │                 是             否
         │                  │              │
         │           ┌──────┴──────┐      │
         │           │转成G judge  │      │
         │           └──────┬──────┘      │
         │                  │             │
         │                  │      ┌──────┴──────┐
         │                  │      │含CK/GC等   │
         │                  │      │关键字？     │
         │                  │      └──────┬──────┘
         │                  │   ┌───────┴───────┐
         │                  │  是               否
         │                  │   │                │
         │                  │┌──┴───┐       ┌────┴────┐
         │                  ││转成S  │       │转成Q    │
         │                  ││judge │       │judge   │
         │                  │└──┬───┘       └────┬────┘
         │                  │   │                │
         └──────────────────┼───┴────────────────┘
                            │
                ┌───────────┴───────────┐
                │ 产品在M1_TO_T1？     │
                │ 且code是M1_SP_PI_*？ │
                └───────────┬───────────┘
                     ┌──────┴──────┐
                    是             否
                     │              │
              ┌──────┴──────┐      │
              │转成T1_SP_PI │      │
              └──────┬──────┘      │
                     │              │
                ┌────┴──────────────┘
                │
    ┌───────────┴───────────┐
    │ 产品不在AS_TO_M2？   │
    │ 且code是M2_SP_PI_*？ │
    └───────────┬───────────┘
         ┌──────┴──────┐
        是             否
         │              │
    ┌────┴────┐   ┌────┴────┐
    │转成AS_  │   │保持M2_  │
    │CV_PI_*  │   │SP_PI_*  │
    └────┬────┘   └────┬────┘
         │              │
         └──────┬───────┘
                │
         ┌──────┴──────┐
         │  最终输出    │
         └─────────────┘
```

---

## 关键注意事项

### 1. 小尺寸M2_SP_PI_P的处理（最重要）
**注意**: 小尺寸产品的M2_SP_PI_P转换有**执行顺序**问题：

| 代码位置 | 转换 | 是否执行 |
|---------|------|---------|
| 588行（result_df阶段） | M2_SP_PI_P → M2_SP_PI_G | ✅ **先执行** |
| 138行（get_judge阶段） | P/L → Q | ❌ **不执行**（judge已经是'G'） |

**结论**: 小产品的 `M2_SP_PI_P` 最终变成 `M2_SP_PI_G`，**不会**变成 `M2_SP_PI_Q`

---

### 2. 无阈值Code的影响
**注意**: 没有定义阈值的code（如M2_SP_PI_Q）会默认保留，即使置信度很低。

**示例**: M2_SP_PI_P (0.597) 阈值0.75 → 被标记为'other' → 被过滤
**示例**: M2_SP_PI_Q (0.059) 无阈值 → 保留 → 成为最终输出

---

### 3. 转换顺序的优先级
**注意**: 转换严格按照代码执行顺序，先执行的转换会影响后续转换：

| 阶段 | 位置 | 转换类型 | 影响 |
|------|------|---------|------|
| 1 | 588行 | 小产品M2_SP_PI_P→G | **阻止**后续P/L→Q |
| 2 | 138行 | 小产品P/L→Q/S/G | judge变更后不再参与 |
| 3 | 155行 | M1→T1 | code变更后不再匹配M2规则 |
| 4 | 162行 | M2→AS | code变更后不再参与转换 |

---

### 4. 产品分类的判断顺序
**注意**: 一个产品可能同时属于多个分类，判断顺序很重要：

```python
# 判断顺序（按代码执行顺序）
1. pro in small_products      # 先判断是否小产品
2. pro in big_products        # 再判断是否大产品
3. pro in M1_TO_T1_products   # 再判断是否需要M1→T1
4. pro in AS_TO_M2_products   # 最后判断是否M2→AS
```

**示例**：
- 产品156: 在 small_products ✓，在 M1_TO_T1 ✓，在 AS_TO_M2 ✓
- 产品238: 不在 small_products，在 M1_TO_T1 ✓，**不在** AS_TO_M2

---

### 5. 特殊Code的阈值差异
**注意**: 某些code的不同judge有不同的阈值：

| Code | Judge | 阈值 |
|------|-------|------|
| M2_DE_BS | G | 0.45 |
| M2_DE_BS | P | 0.5 |
| NP_XX_UN | G | 0.75 |
| NP_XX_UN | P | 0.4 |
| P1_XX_BV | G | 0.5 |
| P1_XX_BV | P | 0.45 |

---

### 6. 特殊列表中的Code不会转Q
**注意**: 以下code在小产品中会转成'G' judge，**不会**转成'Q'：

```
['M1_XX_UO_P', 'M1_XX_UO_L', 'T1_XX_UO_P', 'T1_XX_UO_L',
 'M2_XX_UO_P', 'M2_XX_UO_L', 'M2_XX_SA_P', 'AS_CV_SA_P',
 'P1_CV_SA_P', 'T3_XX_UO_P', 'T3_XX_UO_L', 'AS_XX_UO_P',
 'T3_SP_PI_P']
```

---

### 7. 关键字判断优先于通用Q转换
**注意**: 包含关键字的code会转成'S' judge，**不会**转成'Q'：

```
关键字: 'CK', 'GC', 'GD', 'SC', 'AC', 'ES'
```

---

### 8. 产品156的特殊判断
**注意**: 产品156在M1_TO_T1中，但有特殊情况：

```python
if pro == '156' and product != 'H4A156FDF04':
    pass  # 不转换，保持M1_SP_PI
else:
    code = 'T1_' + code[3:]  # 转换成T1_SP_PI
```

**结论**：
- `H4A156FDF04`: M1_SP_PI_P → T1_SP_PI_P ✓
- `H4A156HDF01`: M1_SP_PI_P → M1_SP_PI_P（不转换）

---

### 9. AS_TO_M2产品的范围
**注意**: AS_TO_M2_products包含小产品和部分中产品：

```
小产品: 020-095
中产品: 101, 109, 116, 140, 156
```

**结论**：
- 产品020-095: M2_SP_PI_P → M2_SP_PI_G（588行）→ 不再参与162行转换
- 产品101/109/116/140/156: M2_SP_PI_P → 直接参与162行判断，保持M2_SP_PI（因为在AS_TO_M2中）
- 其他产品: M2_SP_PI_P → AS_CV_PI_P（162行转换）

---

### 10. 转换后的Code不再参与后续判断
**注意**: 一旦code被转换，会立即更新judge和code值，后续判断使用新值：

**示例**：
```python
# 原code: M1_XX_UO_P, judge='P'
# 138行转换: code='M1_XX_UO_G', judge='G'
# 后续162行判断: 使用的是新code='M1_XX_UO_G'，不再匹配M2_SP_PI规则
```

---

## 版本信息
- **项目**: A9950_model_dev
- **生成时间**: 2026-01-12
- **文档版本**: 1.0
