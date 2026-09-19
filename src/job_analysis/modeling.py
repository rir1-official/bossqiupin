"""Train and compare four models for the information-quality proxy label."""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import LinearSVC
from sklearn.feature_extraction.text import TfidfVectorizer
from xgboost import XGBClassifier

from .cleaning import PROJECT_ROOT, ensure_derived_output
from .visualization import PALETTE, configure_style, save_figure


INPUT_PATH = PROJECT_ROOT / "data/processed/jobs_cleaned.parquet"
MODEL_DIR = PROJECT_ROOT / "data/processed/models"
REPORT_DIR = PROJECT_ROOT / "reports/modeling"
DOC_PATH = PROJECT_ROOT / "docs/job_quality_scoring_model.md"

NUMERIC_FEATURES = [
    "description_length",
    "description_word_count",
    "description_structure_count",
    "skill_count",
    "location_restriction_count",
    "publish_age_days",
    "experience_year_min",
    "experience_year_max",
]
CATEGORICAL_FEATURES = ["experience_level_primary", "broad_category"]
TEXT_FEATURE = "model_text"


def prepare_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    frame = df.copy()
    frame[TEXT_FEATURE] = (
        frame["job_title"].fillna("")
        + " "
        + frame["job_category"].fillna("")
        + " "
        + frame["skills_normalized"].fillna("")
        + " "
        + frame["description_clean"].fillna("")
    )
    return frame[NUMERIC_FEATURES + CATEGORICAL_FEATURES + [TEXT_FEATURE]], frame["quality_label"].astype(int)


def make_preprocessor() -> ColumnTransformer:
    numeric = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
            ("scaler", StandardScaler()),
        ]
    )
    categorical = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    return ColumnTransformer(
        [
            ("numeric", numeric, NUMERIC_FEATURES),
            ("categorical", categorical, CATEGORICAL_FEATURES),
            (
                "text",
                TfidfVectorizer(max_features=4_000, min_df=3, max_df=0.98, ngram_range=(1, 2), sublinear_tf=True),
                TEXT_FEATURE,
            ),
        ]
    )


def model_specs() -> Dict[str, Any]:
    return {
        "Logistic Regression": LogisticRegression(max_iter=3_000, class_weight="balanced", random_state=42),
        "SVM (LinearSVC)": LinearSVC(class_weight="balanced", random_state=42, max_iter=10_000),
        "Random Forest": RandomForestClassifier(
            n_estimators=300,
            max_depth=14,
            min_samples_leaf=2,
            class_weight="balanced",
            n_jobs=-1,
            random_state=42,
        ),
        "XGBoost": XGBClassifier(
            n_estimators=300,
            max_depth=5,
            learning_rate=0.06,
            subsample=0.85,
            colsample_bytree=0.85,
            eval_metric="logloss",
            n_jobs=4,
            random_state=42,
        ),
    }


def score_values(pipeline: Pipeline, x_test: pd.DataFrame) -> np.ndarray:
    if hasattr(pipeline, "predict_proba"):
        return pipeline.predict_proba(x_test)[:, 1]
    return pipeline.decision_function(x_test)


def evaluate(y_true: pd.Series, y_pred: np.ndarray, scores: np.ndarray) -> Dict[str, float]:
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "roc_auc": roc_auc_score(y_true, scores),
    }


def safe_model_name(name: str) -> str:
    return name.lower().replace(" ", "_").replace("(", "").replace(")", "")


def plot_confusion_matrices(results: Dict[str, Dict[str, Any]], y_test: pd.Series) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(10, 9))
    for ax, (name, result) in zip(axes.flat, results.items()):
        ConfusionMatrixDisplay.from_predictions(
            y_test,
            result["predictions"],
            display_labels=["Not high", "High"],
            cmap="Greens",
            colorbar=False,
            ax=ax,
        )
        ax.set_title(name)
    fig.suptitle("四模型测试集混淆矩阵", fontsize=16, fontweight="bold")
    fig.tight_layout()
    save_figure(fig, REPORT_DIR / "confusion_matrices.png")


def plot_roc_curves(results: Dict[str, Dict[str, Any]], y_test: pd.Series) -> None:
    fig, ax = plt.subplots(figsize=(8, 6.5))
    for index, (name, result) in enumerate(results.items()):
        false_positive, true_positive, _ = roc_curve(y_test, result["scores"])
        ax.plot(false_positive, true_positive, linewidth=2, color=PALETTE[index], label=f"{name} (AUC={result['metrics']['roc_auc']:.3f})")
    ax.plot([0, 1], [0, 1], linestyle="--", color="#777777", linewidth=1)
    ax.set(title="四模型 ROC 曲线", xlabel="假阳性率", ylabel="真阳性率")
    ax.legend(frameon=False, loc="lower right")
    save_figure(fig, REPORT_DIR / "roc_curves.png")


def plot_model_comparison(metrics: pd.DataFrame) -> None:
    long = metrics.melt(id_vars="model", value_vars=["accuracy", "precision", "recall", "f1", "roc_auc"], var_name="metric", value_name="score")
    fig, ax = plt.subplots(figsize=(11, 6))
    import seaborn as sns

    sns.barplot(data=long, x="model", y="score", hue="metric", palette=PALETTE[:5], ax=ax)
    ax.set(title="岗位信息质量标签：四模型指标对比", xlabel="模型", ylabel="测试集得分", ylim=(0, 1.05))
    ax.tick_params(axis="x", rotation=15)
    ax.legend(frameon=False, ncol=3)
    save_figure(fig, REPORT_DIR / "model_comparison.png")


def feature_importance(pipeline: Pipeline, model_name: str) -> pd.DataFrame:
    preprocessor = pipeline.named_steps["preprocessor"]
    names = preprocessor.get_feature_names_out()
    classifier = pipeline.named_steps["classifier"]
    if hasattr(classifier, "feature_importances_"):
        values = classifier.feature_importances_
    elif hasattr(classifier, "coef_"):
        values = np.abs(classifier.coef_[0])
    else:
        return pd.DataFrame(columns=["feature", "importance", "model"])
    return pd.DataFrame({"feature": names, "importance": values, "model": model_name}).sort_values("importance", ascending=False)


def plot_importance(frame: pd.DataFrame, model_name: str) -> None:
    top = frame.head(20).sort_values("importance")
    fig, ax = plt.subplots(figsize=(9, 7))
    ax.barh(top["feature"].str.replace("numeric__", "", regex=False).str.replace("categorical__", "", regex=False), top["importance"], color=PALETTE[0])
    ax.set(title=f"{model_name}：Top 20 特征重要性", xlabel="重要性（模型内部尺度）", ylabel="特征")
    ax.grid(axis="y", visible=False)
    save_figure(fig, REPORT_DIR / f"feature_importance_{safe_model_name(model_name)}.png")


def write_document(metrics: pd.DataFrame, train_count: int, test_count: int, positive_rate: float, importances: pd.DataFrame) -> None:
    table = metrics.copy()
    for column in ["accuracy", "precision", "recall", "f1", "roc_auc"]:
        table[column] = table[column].map(lambda value: f"{value:.4f}")
    headers = list(table.columns)
    markdown_rows = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] + ["---:"] * (len(headers) - 1)) + " |",
    ]
    markdown_rows.extend("| " + " | ".join(map(str, row)) + " |" for row in table.itertuples(index=False, name=None))
    markdown_table = "\n".join(markdown_rows)
    top_rf = importances.loc[importances["model"].eq("Random Forest")].head(8)
    importance_text = "、".join(
        f"`{row.feature.replace('numeric__', '').replace('categorical__', '')}` ({row.importance:.3f})"
        for row in top_rf.itertuples()
    )
    best = metrics.sort_values(["f1", "roc_auc"], ascending=False).iloc[0]
    text = f"""# 岗位质量评分模型

## 1. 业务定义

本项目的“岗位质量”严格定义为岗位信息透明度与完整度，不是雇主信誉、工作体验或候选人录用概率。规则分总计 100 分，涵盖追溯字段、核心字段、地点限制、描述完整性、薪资透明度、技能清晰度、职级、时效性和类别；分数达到 80 定义为高信息质量（`quality_label=1`）。这是课程用代理标签，不是人工真实标签。

## 2. 数据与实验设计

- 去重后样本：{train_count + test_count:,} 条；高信息质量占 {positive_rate:.1%}。
- 固定随机种子 42，按标签分层拆分：训练集 {train_count:,} 条，测试集 {test_count:,} 条（80/20）。
- 数值特征缺失以训练集内中位数填补并标准化；类别特征以众数填补并独热编码。
- 输入包含岗位文本 TF-IDF、描述长度/结构、技能数、地点限制、发布时间、经验代理和宽类岗位。为避免确定性泄漏，明确排除薪资披露标记、币种、周期、`quality_score`、各规则分项和标签本身。
- 四模型使用同一数据拆分和同一特征预处理，评价 Accuracy、Precision、Recall、F1 与 ROC-AUC。

## 3. 测试集结果

{markdown_table}

按 F1 优先、ROC-AUC 次优的规则，当前表现最好的是 **{best['model']}**（F1={best['f1']:.4f}，ROC-AUC={best['roc_auc']:.4f}）。

![模型指标对比](../reports/modeling/model_comparison.png)

![混淆矩阵](../reports/modeling/confusion_matrices.png)

![ROC 曲线](../reports/modeling/roc_curves.png)

## 4. 可解释性

Random Forest 的主要特征为：{importance_text}。特征重要性表示模型在复现规则标签时使用这些变量的相对程度，不代表因果影响。树模型完整 Top 20 图和 CSV 均保存在 `reports/modeling/`。

## 5. 局限与答辩口径

指标高并不意味着模型已经识别真实好岗位，因为标签由同一份岗位信息中的固定规则生成，模型评价的是规则可学习性。当前最重要的外部效度缺口是没有候选人反馈、录用结果、企业信誉和人工双人标注。答辩时应称其为“岗位信息质量评分模型”；下一阶段可抽样 300 至 500 条由两名标注者独立评价，报告一致性，并用人工标签重新训练和校准阈值。
"""
    ensure_derived_output(DOC_PATH)
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text(text, encoding="utf-8")


def run(input_path: Path = INPUT_PATH) -> pd.DataFrame:
    configure_style()
    df = pd.read_parquet(input_path)
    x, y = prepare_features(df)
    indices = np.arange(len(df))
    train_idx, test_idx = train_test_split(indices, test_size=0.2, random_state=42, stratify=y)
    x_train, x_test = x.iloc[train_idx], x.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    results: Dict[str, Dict[str, Any]] = {}
    importance_frames: List[pd.DataFrame] = []
    prediction_export = df.iloc[test_idx][["job_id", "source_url", "crawl_time", "data_origin", "quality_score", "quality_label"]].copy()
    for name, classifier in model_specs().items():
        pipeline = Pipeline([("preprocessor", make_preprocessor()), ("classifier", classifier)])
        pipeline.fit(x_train, y_train)
        predictions = pipeline.predict(x_test)
        scores = score_values(pipeline, x_test)
        metrics = evaluate(y_test, predictions, scores)
        results[name] = {"pipeline": pipeline, "predictions": predictions, "scores": scores, "metrics": metrics}
        joblib.dump(pipeline, MODEL_DIR / f"{safe_model_name(name)}.joblib")
        prediction_export[f"prediction_{safe_model_name(name)}"] = predictions
        prediction_export[f"score_{safe_model_name(name)}"] = scores
        frame = feature_importance(pipeline, name)
        if not frame.empty:
            importance_frames.append(frame)
            if name in {"Random Forest", "XGBoost", "Logistic Regression"}:
                plot_importance(frame, name)

    metrics = pd.DataFrame([{"model": name, **result["metrics"]} for name, result in results.items()])
    metrics.to_csv(REPORT_DIR / "model_metrics.csv", index=False)
    (REPORT_DIR / "model_metrics.json").write_text(metrics.to_json(orient="records", indent=2), encoding="utf-8")
    prediction_export.to_csv(REPORT_DIR / "test_predictions.csv", index=False, encoding="utf-8-sig")
    importances = pd.concat(importance_frames, ignore_index=True)
    importances.to_csv(REPORT_DIR / "feature_importance.csv", index=False)
    plot_confusion_matrices(results, y_test)
    plot_roc_curves(results, y_test)
    plot_model_comparison(metrics)
    write_document(metrics, len(train_idx), len(test_idx), float(y.mean()), importances)
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Train four information-quality models")
    parser.add_argument("--input", type=Path, default=INPUT_PATH)
    args = parser.parse_args()
    metrics = run(args.input)
    print(metrics.to_json(orient="records", indent=2))


if __name__ == "__main__":
    main()
